"""The leasing model, compiled to DuckDB macros.

Why this exists: the advisor's headline feature is *affordability-first search*
— "find me something for €300 a month" — which means ranking 45k listings by
monthly rate, not by price. Quoting each candidate in Python would mean
fetching rows first and pricing them after, i.e. filtering on the wrong key.

So the same model runs in two engines:

* `cars_leasing.model.compute_quote` — authoritative. Every rate a customer is
  ever told, and every rate that goes into an email, comes from here.
* these macros — a ranking approximation used *only* to sort and filter inside
  SQL, so `WHERE monthly_rate <= 300` is a real predicate over the full table.

Both are generated from the same constants in `model.py`, so they cannot drift.
`tests/test_leasing_parity.py` asserts they agree to the cent on real rows.
"""

from __future__ import annotations

from cars_leasing.model import (
    AGE_FLATTENING,
    APR,
    BASE_ANNUAL_DECAY,
    EXTRA_KM_VALUE,
    FUEL_DECAY,
    MAX_DOWN_PAYMENT_SHARE,
    MAX_END_AGE_YEARS,
    MAX_END_MILEAGE_KM,
    MIN_PRICE,
    NORMAL_ANNUAL_KM,
    RESIDUAL_FLOOR,
)


def _decay_case() -> str:
    """SQL CASE mirroring FUEL_DECAY's per-fuel overrides."""
    whens = "\n        ".join(
        f"WHEN {fuel!r} THEN {rate}" for fuel, rate in FUEL_DECAY.items()
    )
    return f"CASE fuel_category\n        {whens}\n        ELSE {BASE_ANNUAL_DECAY} END"


def macro_ddl() -> str:
    """DDL registering the leasing macros; run once per connection."""
    residual = f"""
    greatest(
      price * pow(1.0 - ({_decay_case()}) * pow({AGE_FLATTENING}, age_years),
                  term_months / 12.0)
        - (annual_km - {NORMAL_ANNUAL_KM}) * (term_months / 12.0) * {EXTRA_KM_VALUE},
      {RESIDUAL_FLOOR} * price)
    """
    return f"""
CREATE OR REPLACE MACRO lease_age_years(reg_date) AS
  greatest(0, date_part('year', current_date) - date_part('year', reg_date));

CREATE OR REPLACE MACRO lease_residual(
    price, age_years, fuel_category, term_months, annual_km) AS ({residual});

CREATE OR REPLACE MACRO lease_rate(
    price, age_years, fuel_category, term_months, annual_km, down_payment) AS (
  ((price - down_payment)
     - lease_residual(price, age_years, fuel_category, term_months, annual_km))
    / term_months
  + ((price - down_payment)
     + lease_residual(price, age_years, fuel_category, term_months, annual_km))
    * {APR} / 24.0);

-- Every eligibility rule compute_quote() enforces, evaluated in SQL, so search
-- can only ever return cars that will actually produce a quote.
CREATE OR REPLACE MACRO lease_eligible(
    price, seller_type, age_years, mileage_km, fuel_category,
    term_months, annual_km, down_payment) AS (
  seller_type = 'Dealer'
  AND price >= {MIN_PRICE}
  AND age_years + term_months / 12.0 <= {MAX_END_AGE_YEARS}
  AND mileage_km + annual_km * (term_months / 12.0) <= {MAX_END_MILEAGE_KM}
  AND down_payment BETWEEN 0 AND {MAX_DOWN_PAYMENT_SHARE} * price
  AND (price - down_payment)
      >= lease_residual(price, age_years, fuel_category, term_months, annual_km));
"""
