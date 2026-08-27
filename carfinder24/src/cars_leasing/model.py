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
class ChoiceProblem:
    """One thing the customer asked for that we do not offer.

    `message` is a whole sentence written to be read out loud, and `allowed`
    carries the buckets to offer instead — so a refusal always comes with the
    choices that would work.
    """

    field: str  # term_months | annual_km | down_payment | price
    message: str
    allowed: tuple[int, ...] | None = None


class InvalidChoice(NotLeasable):
    """The customer's terms are outside what CarFinder24 offers.

    Distinct from a plain NotLeasable (which is about *this car*): here the
    inputs themselves are unavailable, so the fix is to pick from `.problems`'
    allowed buckets. No sale proceeds until they do.
    """

    def __init__(self, problems: tuple[ChoiceProblem, ...] | list[ChoiceProblem]) -> None:
        self.problems: tuple[ChoiceProblem, ...] = tuple(problems)
        super().__init__(" ".join(p.message for p in self.problems))


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
    price: int  # the listing price the quote was built from


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
    # Everything the customer *chose* is checked in one place, so an
    # impossible request always comes back with the buckets that would work.
    require_valid_choices(
        term_months=term_months,
        annual_km=annual_km,
        down_payment=down_payment,
        price=price,
    )

    if seller_type != "Dealer":
        raise NotLeasable("Only dealer listings can be leased, this is a private sale.")

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
        price=price,
    )


# ---------------------------------------------------------------------------
# What a customer may choose
#
# Terms and mileage tiers are *buckets*, not free numbers: a lessor prices
# 36 months / 15,000 km, not "about three years, maybe forty thousand". So a
# value outside a bucket is not rounded to the nearest one — silently moving a
# customer onto terms they did not ask for is how a voice agent sells the wrong
# contract. It is refused, and the refusal names the buckets that do exist.
# ---------------------------------------------------------------------------


def validate_choices(
    *,
    term_months: int | None = None,
    annual_km: int | None = None,
    down_payment: int | None = None,
    price: int | None = None,
) -> tuple[ChoiceProblem, ...]:
    """Check the customer's choices against what we offer. Never raises.

    Only the arguments that are not None are checked, so this works both for a
    half-collected conversation and for a complete request. `price` is the
    listing price — needed to bound the down payment, and checked against the
    floor when given.
    """
    problems: list[ChoiceProblem] = []

    if term_months is not None and term_months not in TERMS:
        problems.append(
            ChoiceProblem(
                "term_months",
                f"We lease for {_spoken_list(TERMS)} months — "
                f"{term_months} months is not one of our terms.",
                TERMS,
            )
        )
    if annual_km is not None and annual_km not in KM_TIERS:
        problems.append(
            ChoiceProblem(
                "annual_km",
                f"The mileage allowances are {_spoken_list(KM_TIERS)} kilometres "
                f"a year — {_grouped(annual_km)} is not one of them.",
                KM_TIERS,
            )
        )
    if price is not None and price < MIN_PRICE:
        problems.append(
            ChoiceProblem(
                "price",
                f"Leasing starts at a car price of \u20ac{_grouped(MIN_PRICE)}, so "
                "this one can only be bought, not leased.",
            )
        )
    if down_payment is not None:
        if down_payment < 0:
            problems.append(
                ChoiceProblem("down_payment", "A down payment cannot be negative.")
            )
        elif price is not None and down_payment > MAX_DOWN_PAYMENT_SHARE * price:
            cap = int(MAX_DOWN_PAYMENT_SHARE * price)
            problems.append(
                ChoiceProblem(
                    "down_payment",
                    f"The down payment can be at most {MAX_DOWN_PAYMENT_SHARE:.0%} of "
                    f"the price, so up to \u20ac{_grouped(cap)} for this car.",
                )
            )
    return tuple(problems)


def require_valid_choices(**kwargs: int | None) -> None:
    """validate_choices, but raising InvalidChoice — use before quoting."""
    if problems := validate_choices(**kwargs):
        raise InvalidChoice(problems)


def leasing_options(price: int | None = None) -> dict[str, object]:
    """Everything a customer is allowed to pick — the answer to "what can I have?".

    Handed straight to the model when a request is refused, so the next
    sentence out of the advisor is the list of terms that would work.
    """
    options: dict[str, object] = {
        "term_months": list(TERMS),
        "annual_km": list(KM_TIERS),
        "min_price_eur": MIN_PRICE,
        "max_down_payment_share": MAX_DOWN_PAYMENT_SHARE,
        "max_car_age_at_end_years": MAX_END_AGE_YEARS,
        "max_odometer_at_end_km": MAX_END_MILEAGE_KM,
        "contract_type": "Kilometerleasing, private customer, gross rate incl. VAT",
    }
    if price is not None:
        options["max_down_payment_eur"] = int(MAX_DOWN_PAYMENT_SHARE * price)
    return options


def _grouped(value: int) -> str:
    """15000 -> '15 000'; a comma here would be read as a pause."""
    return f"{value:,}".replace(",", " ")


def _spoken_list(values: tuple[int, ...]) -> str:
    """'12, 24, 36 or 48' — a list a voice model can read without stumbling."""
    parts = [_grouped(v) for v in values]
    return f"{', '.join(parts[:-1])} or {parts[-1]}" if len(parts) > 1 else parts[0]
