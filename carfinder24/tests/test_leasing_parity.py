"""The SQL leasing macros must agree with the Python model, to the cent.

`search_cars` ranks 45k listings by a monthly rate computed in DuckDB, then the
customer is quoted a rate computed in Python. If those two ever disagree, the
advisor offers one number and bills another — the single worst failure this
system could have. This test is the guard: same constants, same arithmetic,
verified on real rows across every term and mileage tier.
"""

from __future__ import annotations

import pytest

from cars_leasing.model import NotLeasable, TERMS, KM_TIERS, compute_quote
from cars_mcp.server import get_db


@pytest.fixture(scope="module")
def db():
    return get_db()


@pytest.mark.parametrize("term_months", TERMS)
@pytest.mark.parametrize("annual_km", KM_TIERS)
def test_sql_rate_matches_python_quote(db, term_months: int, annual_km: int) -> None:
    rows = db.query(
        """
        SELECT id, price, mileage_km, seller_type, fuel_category, registration_date,
               lease_age_years(registration_date) AS age_years,
               lease_rate(price, lease_age_years(registration_date),
                          fuel_category, $term, $km, 0) AS sql_rate
        FROM ads
        WHERE registration_date IS NOT NULL AND price IS NOT NULL
          AND mileage_km IS NOT NULL
          AND lease_eligible(price, seller_type,
                             lease_age_years(registration_date), mileage_km,
                             fuel_category, $term, $km, 0)
        USING SAMPLE 40 ROWS (reservoir, 42)
        """,
        {"term": term_months, "km": annual_km},
    )
    assert rows, "eligible sample should not be empty"
    for row in rows:
        quote = compute_quote(
            price=row["price"],
            registration_year=row["registration_date"].year,
            mileage_km=row["mileage_km"],
            seller_type=row["seller_type"],
            term_months=term_months,
            annual_km=annual_km,
            fuel_category=row["fuel_category"],
        )
        assert round(row["sql_rate"], 2) == pytest.approx(quote.monthly_rate, abs=0.01), (
            f"listing {row['id']}: SQL {row['sql_rate']} vs Python {quote.monthly_rate}"
        )


def test_sql_eligibility_matches_python(db) -> None:
    """Anything SQL calls eligible must actually produce a quote — no dead ends."""
    rows = db.query(
        """
        SELECT price, mileage_km, seller_type, fuel_category, registration_date
        FROM ads
        WHERE registration_date IS NOT NULL AND price IS NOT NULL AND mileage_km IS NOT NULL
          AND lease_eligible(price, seller_type, lease_age_years(registration_date),
                             mileage_km, fuel_category, 48, 30000, 0)
        USING SAMPLE 150 ROWS (reservoir, 7)
        """
    )
    for row in rows:
        compute_quote(  # must not raise
            price=row["price"], registration_year=row["registration_date"].year,
            mileage_km=row["mileage_km"], seller_type=row["seller_type"],
            term_months=48, annual_km=30_000, fuel_category=row["fuel_category"],
        )


def test_private_sellers_are_never_eligible(db) -> None:
    (row,) = db.query(
        """
        SELECT count(*) AS n FROM ads
        WHERE seller_type <> 'Dealer' AND registration_date IS NOT NULL
          AND price IS NOT NULL AND mileage_km IS NOT NULL
          AND lease_eligible(price, seller_type, lease_age_years(registration_date),
                             mileage_km, fuel_category, 36, 15000, 0)
        """
    )
    assert row["n"] == 0
    with pytest.raises(NotLeasable):
        compute_quote(price=20_000, registration_year=2021, mileage_km=50_000,
                      seller_type="PrivateSeller", term_months=36, annual_km=15_000)
