"""What happens when a customer asks for terms we do not offer.

The failure this guards against is a voice agent quietly rounding "about forty
thousand kilometres" down to the 30,000 tier, or a 30-month wish up to 36, and
selling a contract nobody agreed to. The rule is: refuse, name the buckets that
exist, and do not proceed.
"""

from __future__ import annotations

import pytest

from cars_leasing.explain import explain_leasing
from cars_leasing.model import (
    KM_TIERS,
    MAX_DOWN_PAYMENT_SHARE,
    MIN_PRICE,
    TERMS,
    InvalidChoice,
    NotLeasable,
    compute_quote,
    leasing_options,
    validate_choices,
)
from cars_mcp.server import leasing_quote, search_cars


@pytest.fixture(scope="module")
def leasable_ref() -> str:
    return search_cars(max_monthly_rate=400, limit=1)["cars"][0]["ref"]


# --- the validator itself ---------------------------------------------------


@pytest.mark.parametrize("term", [0, 6, 7, 30, 36.5, 60, -12])
def test_a_term_we_do_not_offer_is_refused(term) -> None:
    (problem,) = validate_choices(term_months=term)
    assert problem.field == "term_months"
    assert problem.allowed == TERMS


@pytest.mark.parametrize("km", [0, 5_000, 12_345, 25_000, 40_000, 100_000])
def test_a_mileage_tier_we_do_not_offer_is_refused(km) -> None:
    (problem,) = validate_choices(annual_km=km)
    assert problem.field == "annual_km"
    assert problem.allowed == KM_TIERS


def test_valid_choices_produce_no_complaint() -> None:
    for term in TERMS:
        for km in KM_TIERS:
            assert validate_choices(term_months=term, annual_km=km, down_payment=0,
                                    price=20_000) == ()


def test_a_car_below_the_price_floor_cannot_be_leased() -> None:
    (problem,) = validate_choices(price=MIN_PRICE - 1)
    assert problem.field == "price"
    assert "bought" in problem.message


def test_a_down_payment_over_half_the_price_is_refused() -> None:
    price = 20_000
    cap = int(MAX_DOWN_PAYMENT_SHARE * price)
    assert validate_choices(down_payment=cap, price=price) == ()
    (problem,) = validate_choices(down_payment=cap + 1, price=price)
    assert problem.field == "down_payment"
    assert validate_choices(down_payment=-1, price=price)[0].field == "down_payment"


def test_every_bad_choice_is_reported_at_once() -> None:
    """One refusal listing everything wrong, not four rounds of trial and error."""
    problems = validate_choices(
        term_months=30, annual_km=40_000, down_payment=99_000, price=1_000
    )
    assert {p.field for p in problems} == {
        "term_months", "annual_km", "down_payment", "price",
    }


def test_a_refusal_always_names_the_choices_that_exist() -> None:
    (problem,) = validate_choices(term_months=30)
    for term in TERMS:
        assert str(term) in problem.message


# --- nothing proceeds past a bad choice -------------------------------------


def test_quoting_impossible_terms_raises_rather_than_rounding() -> None:
    with pytest.raises(InvalidChoice) as caught:
        compute_quote(
            price=20_000, registration_year=2021, mileage_km=50_000,
            seller_type="Dealer", term_months=30, annual_km=40_000,
        )
    assert {p.field for p in caught.value.problems} == {"term_months", "annual_km"}
    assert isinstance(caught.value, NotLeasable)  # callers catching the old type still work


def test_the_tool_declines_and_offers_the_alternatives(leasable_ref) -> None:
    result = leasing_quote(leasable_ref, term_months=30, annual_km=40_000)
    assert "monthly_rate_eur" not in result  # no sale proceeds
    assert {entry["field"] for entry in result["invalid"]} == {"term_months", "annual_km"}
    assert result["options"]["term_months"] == list(TERMS)
    assert result["options"]["annual_km"] == list(KM_TIERS)


def test_search_refuses_impossible_terms_instead_of_returning_cars() -> None:
    result = search_cars(max_monthly_rate=300, term_months=30)
    assert "cars" not in result
    assert result["invalid"][0]["allowed"] == list(TERMS)


def test_a_declined_car_still_gets_the_options(leasable_ref) -> None:
    """Even a refusal about the car (not the terms) ends with what would work."""
    result = leasing_quote(leasable_ref, term_months=48, annual_km=30_000,
                           down_payment=10_000_000)
    assert "declined" in result
    assert result["options"]["term_months"] == list(TERMS)


def test_leasing_options_lists_everything_a_customer_may_pick() -> None:
    options = leasing_options(price=20_000)
    assert options["term_months"] == list(TERMS)
    assert options["annual_km"] == list(KM_TIERS)
    assert options["max_down_payment_eur"] == 10_000


# --- the transparency function ----------------------------------------------


def test_the_explanation_reproduces_the_quote_it_explains() -> None:
    """Every number the advisor reads out is the one that was actually charged."""
    quote = compute_quote(
        price=24_900, registration_year=2021, mileage_km=64_000, seller_type="Dealer",
        term_months=36, annual_km=15_000, down_payment=2_000, fuel_category="Diesel",
    )
    worked = explain_leasing(quote)["worked_example"]
    assert f"{quote.monthly_depreciation:,.2f}".replace(",", " ") in worked["monthly_rate"]
    assert f"{quote.monthly_finance:,.2f}".replace(",", " ") in worked["monthly_rate"]
    assert f"{quote.monthly_rate:,.2f}".replace(",", " ") in worked["monthly_rate"]
    assert f"{quote.total_cost:,.2f}".replace(",", " ") in worked["total_over_the_term"]


def test_the_explanation_carries_the_real_constants() -> None:
    constants = explain_leasing()["constants"]
    assert constants["terms_months"] == list(TERMS)
    assert constants["mileage_tiers_km"] == list(KM_TIERS)
    assert constants["min_car_price_eur"] == MIN_PRICE
    assert constants["nominal_annual_rate_pct"] > 0
    assert len(explain_leasing()["steps"]) >= 5


def test_the_explanation_is_honest_about_what_is_not_included() -> None:
    explanation = explain_leasing()
    assert "insurance" in explanation["not_included"]
    assert "tyres" in explanation["not_included"]
    assert "no arrangement fee" in explanation["no_hidden_fees"]
