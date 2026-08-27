"""The advisor's own layer: it refuses bad terms, and it remembers what was said.

Both used to be left to the model. Snapping a spoken "about forty thousand" to
the nearest tier put customers on contracts they never chose, and building the
closing summary from the model's recollection let it summarise preferences
nobody stated. Neither is possible now, and these tests keep it that way.
"""

from __future__ import annotations

import pytest

from used_car_advisor.state import Consultation
from used_car_advisor.tools import ADVISOR_TOOLS, KM_TIERS, TERMS, _check_choices

# --- no silent rounding -----------------------------------------------------


@pytest.mark.parametrize("term", TERMS)
def test_a_term_we_offer_passes_straight_through(term) -> None:
    assert _check_choices(term, 15_000) is None


@pytest.mark.parametrize("km", KM_TIERS)
def test_a_tier_we_offer_passes_straight_through(km) -> None:
    assert _check_choices(36, km) is None


@pytest.mark.parametrize(("term", "annual_km"), [(30, 15_000), (36, 40_000), (18, 25_000)])
def test_anything_else_is_refused_with_the_list_of_what_exists(term, annual_km) -> None:
    refusal = _check_choices(term, annual_km)
    assert refusal is not None
    assert "do not search, quote or send anything" in refusal
    for allowed in TERMS if term not in TERMS else KM_TIERS:
        assert f"{allowed:,}".replace(",", " ") in refusal


def test_the_refusal_never_names_the_value_as_if_it_were_available() -> None:
    refusal = _check_choices(30, 15_000)
    assert "30 months is not something I can offer" in refusal


def test_the_advisor_exposes_the_whole_funnel() -> None:
    names = {tool.info.name for tool in ADVISOR_TOOLS}
    assert {
        "advise_car_type", "find_cars", "show_car", "check_price", "leasing_options",
        "quote_leasing", "explain_leasing", "summarize_choices", "email_offer",
    } <= names


# --- the consultation record ------------------------------------------------


def test_what_the_customer_said_is_kept() -> None:
    consultation = Consultation()
    consultation.record(body_type="estate", budget_monthly_eur=300)
    assert consultation.as_kwargs()["body_type"] == "estate"
    assert consultation.as_kwargs()["budget_monthly_eur"] == 300


def test_a_later_answer_replaces_an_earlier_one() -> None:
    consultation = Consultation()
    consultation.record(color="black")
    consultation.record(color="blue")
    assert consultation.color == "blue"


def test_a_missing_answer_never_erases_one_already_given() -> None:
    """A tool called without a colour must not forget the colour they asked for."""
    consultation = Consultation()
    consultation.record(color="black", term_months=36)
    consultation.record(color=None, annual_km=20_000)
    assert consultation.color == "black"
    assert consultation.term_months == 36


def test_unset_answers_are_not_passed_on_as_facts() -> None:
    consultation = Consultation()
    consultation.record(ref="a1b2c3d4")
    kwargs = consultation.as_kwargs()
    assert kwargs["ref"] == "a1b2c3d4"
    assert "color" not in kwargs
    assert "budget_monthly_eur" not in kwargs


def test_the_record_matches_what_the_summary_tool_accepts() -> None:
    """as_kwargs() is handed straight to decision_summary — the names must line up."""
    import inspect

    from cars_mcp.server import decision_summary

    consultation = Consultation()
    consultation.record(
        used_for="family", must_have="big boot", body_type="estate", fuel="diesel",
        transmission="automatic", color="black", max_mileage_km=120_000,
        budget_monthly_eur=350, term_months=36, annual_km=15_000, down_payment=1_000,
        ref="a1b2c3d4",
    )
    accepted = set(inspect.signature(decision_summary).parameters)
    assert set(consultation.as_kwargs()) <= accepted
