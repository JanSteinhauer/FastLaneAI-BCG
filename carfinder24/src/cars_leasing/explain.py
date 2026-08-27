"""How the monthly rate is calculated — the whole arithmetic, in words.

Customers ask "where does that number come from?", and the honest answer is
not something a language model should improvise: it would paraphrase, round,
and eventually invent a factor nobody priced. So the explanation is *built*
from the same constants `model.py` computes with, step by step, and handed to
the advisor as text it only has to read out.

Two levels, both from one call:

* `steps` — the six things that happen to turn a listing price into a rate,
  each with the formula and the reason it exists;
* `worked_example` — those steps with real euros in them, taken from the
  customer's own quote when there is one.

If a constant in `model.py` changes, this explanation changes with it. That is
the point: there is no second copy of the truth to drift out of date.
"""

from __future__ import annotations

from typing import Any

from cars_leasing.model import (
    AGE_FLATTENING,
    APR,
    BASE_ANNUAL_DECAY,
    EXTRA_KM_VALUE,
    FUEL_DECAY,
    KM_TIERS,
    MAX_END_AGE_YEARS,
    MAX_END_MILEAGE_KM,
    MIN_PRICE,
    NORMAL_ANNUAL_KM,
    RESIDUAL_FLOOR,
    TERMS,
    LeasingQuote,
)

HEADLINE = (
    "You pay for the value the car loses while you drive it, plus interest on "
    "the money tied up in it. Nothing else is in the rate."
)


def _eur(value: float) -> str:
    return f"€{value:,.2f}".replace(",", " ")


def _km(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def explain_leasing(quote: LeasingQuote | None = None) -> dict[str, Any]:
    """The full derivation of a monthly leasing rate, ready to be read aloud.

    Pass the customer's own `quote` to get every step filled in with their
    numbers; without one the structure and the constants are still complete.
    """
    fuel_note = ", ".join(f"{fuel} {rate:.0%}" for fuel, rate in FUEL_DECAY.items())
    steps = [
        {
            "step": 1,
            "what": "Start from the listing price",
            "formula": "capitalised value = listing price − down payment",
            "why": (
                "The down payment is money you pay up front, so it is not "
                "financed and no interest accrues on it."
            ),
        },
        {
            "step": 2,
            "what": "Project what the car is worth at the end of the term",
            "formula": (
                "residual = price × (1 − yearly loss) ^ years, where the yearly "
                f"loss starts at {BASE_ANNUAL_DECAY:.0%} and is multiplied by "
                f"{AGE_FLATTENING} for every year the car is already old"
            ),
            "why": (
                "A used car loses value more slowly than a new one, so the curve "
                f"flattens with age. Electrified cars lose it faster: {fuel_note}."
            ),
        },
        {
            "step": 3,
            "what": "Adjust that residual for your mileage allowance",
            "formula": (
                f"residual − (your km per year − {_km(NORMAL_ANNUAL_KM)}) × years "
                f"× {EXTRA_KM_VALUE:.2f} € per km"
            ),
            "why": (
                f"The curve assumes {_km(NORMAL_ANNUAL_KM)} km a year. Driving more "
                "leaves a car worth less at the end, driving less leaves it worth "
                f"more. The residual never falls below {RESIDUAL_FLOOR:.0%} of "
                "today's price."
            ),
        },
        {
            "step": 4,
            "what": "Split the value you use up across the months",
            "formula": "depreciation per month = (capitalised value − residual) ÷ months",
            "why": "This is the part of the rate that is genuinely your consumption.",
        },
        {
            "step": 5,
            "what": "Add the finance charge",
            "formula": (
                f"finance per month = (capitalised value + residual) × {APR:.4f} ÷ 24"
            ),
            "why": (
                f"A flat {APR:.2%} a year on the capital bound in the car. Dividing "
                "by 24 charges it on the average balance, because what you owe "
                "falls from the full price to the residual over the term."
            ),
        },
        {
            "step": 6,
            "what": "That is your rate",
            "formula": "monthly rate = depreciation + finance charge",
            "why": (
                "Gross, including VAT, for a private customer. It is an indicative "
                "offer, not a credit agreement."
            ),
        },
    ]

    result: dict[str, Any] = {
        "headline": HEADLINE,
        "contract_type": "Kilometerleasing (mileage leasing), private customer",
        "steps": steps,
        "constants": {
            "nominal_annual_rate_pct": round(APR * 100, 2),
            "base_annual_value_loss_pct": round(BASE_ANNUAL_DECAY * 100, 1),
            "age_flattening_factor": AGE_FLATTENING,
            "value_loss_by_fuel_pct": {f: round(r * 100, 1) for f, r in FUEL_DECAY.items()},
            "mileage_assumed_in_the_curve_km": NORMAL_ANNUAL_KM,
            "extra_km_value_eur": EXTRA_KM_VALUE,
            "residual_floor_pct_of_price": round(RESIDUAL_FLOOR * 100, 1),
            "terms_months": list(TERMS),
            "mileage_tiers_km": list(KM_TIERS),
            "min_car_price_eur": MIN_PRICE,
            "max_age_at_end_of_term_years": MAX_END_AGE_YEARS,
            "max_odometer_at_end_of_term_km": MAX_END_MILEAGE_KM,
        },
        "included": [
            "registration of the leasing contract",
            "the mileage allowance you chose",
            "return of the vehicle at normal wear at the end of the term",
        ],
        "not_included": [
            "insurance",
            "road tax",
            "fuel or charging",
            "maintenance and servicing",
            "tyres",
        ],
        "excess_mileage": (
            f"Kilometres beyond your allowance are settled at {EXTRA_KM_VALUE:.2f} € "
            "per kilometre at the end of the term."
        ),
        "ownership": "The vehicle stays the property of the lessor throughout.",
        "no_hidden_fees": (
            "There is no arrangement fee, no administration fee and no margin on "
            "top: the rate is exactly depreciation plus the finance charge."
        ),
    }
    if quote is not None:
        result["worked_example"] = _worked_example(quote)
    return result


def _worked_example(quote: LeasingQuote) -> dict[str, Any]:
    """The same steps, with the customer's own euros substituted in."""
    capitalised = quote.price - quote.down_payment
    used = round(capitalised - quote.residual_value, 2)
    return {
        "term_months": quote.term_months,
        "annual_km": quote.annual_km,
        "listing_price": _eur(quote.price),
        "down_payment": _eur(quote.down_payment),
        "capitalised_value": _eur(capitalised),
        "projected_residual_value": _eur(quote.residual_value),
        "value_used_over_the_term": _eur(used),
        "depreciation_per_month": (
            f"{_eur(used)} ÷ {quote.term_months} = {_eur(quote.monthly_depreciation)}"
        ),
        "finance_per_month": (
            f"({_eur(capitalised)} + {_eur(quote.residual_value)}) × "
            f"{quote.apr:.4f} ÷ 24 = {_eur(quote.monthly_finance)}"
        ),
        "monthly_rate": (
            f"{_eur(quote.monthly_depreciation)} + {_eur(quote.monthly_finance)} "
            f"= {_eur(quote.monthly_rate)}"
        ),
        "total_over_the_term": (
            f"{_eur(quote.down_payment)} + {quote.term_months} × "
            f"{_eur(quote.monthly_rate)} = {_eur(quote.total_cost)}"
        ),
    }
