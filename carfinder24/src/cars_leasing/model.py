"""Hypothetical used-car leasing model (German Kilometerleasing style).

This is deliberately a *plausible* model, not a real lessor's pricing: the
monthly rate is depreciation plus a finance charge on the bound capital, with
the residual value projected from an age-dependent decay curve calibrated so
the ad's current price sits on it. All market assumptions are the constants
below — tweak them freely, they are exercise material, not gospel.

The quote is for private customers; listing prices are gross (incl. VAT), so
the resulting rate is gross as well.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

# -- market assumptions ------------------------------------------------------
APR = 0.0649  # flat annual finance rate on the bound capital
BASE_ANNUAL_DECAY = 0.15  # a young car loses ~15% of its value per year...
AGE_FLATTENING = 0.93  # ...decaying slower the older it already is
FUEL_DECAY = {  # fuel-specific overrides of BASE_ANNUAL_DECAY
    "Electric": 0.20,
    "Electric/Gasoline": 0.18,
    "Electric/Diesel": 0.18,
}
NORMAL_ANNUAL_KM = 15_000  # allowance already priced into the decay curve
EXTRA_KM_VALUE = 0.06  # €/km residual-value adjustment beyond the norm
RESIDUAL_FLOOR = 0.05  # a car never books below 5% of today's price

# -- eligibility limits ------------------------------------------------------
TERMS = (12, 24, 36, 48)
KM_TIERS = (10_000, 15_000, 20_000, 30_000)
MIN_PRICE = 4_000  # nobody leases a €900 car
MAX_END_AGE_YEARS = 10  # car age at the END of the term
MAX_END_MILEAGE_KM = 200_000  # odometer at the END of the term
MAX_DOWN_PAYMENT_SHARE = 0.5


class NotLeasable(ValueError):
    """The deal is declined; str(exc) explains why."""


@dataclass(frozen=True)
class LeasingQuote:
    monthly_rate: float  # EUR gross per month
    monthly_depreciation: float  # share covering the value the car loses
    monthly_finance: float  # share covering interest on the bound capital
    residual_value: float  # projected value at the end of the term
    total_cost: float  # down payment + all monthly rates
    term_months: int
    annual_km: int
    down_payment: int
    apr: float


def compute_quote(
    *,
    price: int,
    registration_year: int,
    mileage_km: int,
    seller_type: str,
    term_months: int,
    annual_km: int,
    down_payment: int = 0,
    fuel_category: str | None = None,
) -> LeasingQuote:
    """Quote a monthly rate for leasing this car, or raise NotLeasable.

    price, registration_year, mileage_km, seller_type and fuel_category are
    the listing's attributes; term_months, annual_km and down_payment are the
    customer's choice.
    """
    if term_months not in TERMS:
        raise NotLeasable(f"term_months must be one of {TERMS}")
    if annual_km not in KM_TIERS:
        raise NotLeasable(f"annual_km must be one of {KM_TIERS}")

    if seller_type != "Dealer":
        raise NotLeasable("Only dealer listings can be leased, this is a private sale.")
    if price < MIN_PRICE:
        raise NotLeasable(f"Cars under €{MIN_PRICE:,} are not leased.")

    years = term_months / 12
    this_year = datetime.datetime.now(tz=datetime.UTC).year
    age_years = max(0, this_year - registration_year)
    if age_years + years > MAX_END_AGE_YEARS:
        raise NotLeasable(
            f"The car would be older than {MAX_END_AGE_YEARS} years at the end "
            "of the term. A shorter term may still be possible."
        )
    if mileage_km + annual_km * years > MAX_END_MILEAGE_KM:
        raise NotLeasable(
            f"The car would exceed {MAX_END_MILEAGE_KM:,} km by the end of the "
            "term. A lower mileage allowance or shorter term may still work."
        )
    if not 0 <= down_payment <= MAX_DOWN_PAYMENT_SHARE * price:
        raise NotLeasable(
            f"The down payment must be between €0 and "
            f"{MAX_DOWN_PAYMENT_SHARE:.0%} of the price."
        )

    # Residual value: continue the decay curve the current price sits on,
    # then adjust for driving more/less than the norm it assumes.
    decay = FUEL_DECAY.get(fuel_category or "", BASE_ANNUAL_DECAY)
    decay *= AGE_FLATTENING**age_years
    residual = price * (1 - decay) ** years
    residual -= (annual_km - NORMAL_ANNUAL_KM) * years * EXTRA_KM_VALUE
    residual = max(residual, RESIDUAL_FLOOR * price)

    capitalized = price - down_payment
    if capitalized < residual:
        raise NotLeasable(
            "The down payment exceeds the value the car is expected to lose "
            "over the term — choose a smaller down payment."
        )

    monthly_depreciation = (capitalized - residual) / term_months
    monthly_finance = (capitalized + residual) * APR / 24
    monthly_rate = round(monthly_depreciation + monthly_finance, 2)

    return LeasingQuote(
        monthly_rate=monthly_rate,
        monthly_depreciation=round(monthly_depreciation, 2),
        monthly_finance=round(monthly_finance, 2),
        residual_value=round(residual, 2),
        total_cost=round(down_payment + monthly_rate * term_months, 2),
        term_months=term_months,
        annual_km=annual_km,
        down_payment=down_payment,
        apr=APR,
    )
