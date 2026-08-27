"""The funnel: vague needs in, a searchable profile out, and a summary at the end.

Also the two commercial rules that must hold whatever the model says: partner
dealers are surfaced first *and disclosed*, and the conversation can only end
in one of three ways.
"""

from __future__ import annotations

import pytest

from cars_mcp import partners
from cars_mcp.advice import nearest_tier, recommend_profile
from cars_mcp.server import (
    advise_car_type,
    car_details,
    closing_options,
    decision_summary,
    get_db,
    search_cars,
)
from used_car_advisor.tools import _has_recommendation

# --- from "I don't know" to a profile ---------------------------------------


def test_a_family_is_steered_to_space_not_to_a_badge() -> None:
    profile = recommend_profile(usage="family", passengers=4)
    assert profile.body_types[0] == "estate"
    assert profile.min_seats == 5
    assert profile.reasons


def test_six_people_only_get_offered_something_that_fits_them() -> None:
    profile = recommend_profile(usage="family", passengers=6)
    assert profile.body_types[0] == "van"
    assert profile.min_seats == 7


def test_city_driving_is_steered_to_something_small() -> None:
    profile = recommend_profile(usage="city")
    assert profile.body_types[0] == "compact"
    assert profile.transmission == "automatic"  # stop-and-go


def test_electric_is_only_recommended_to_someone_who_can_charge() -> None:
    can = recommend_profile(usage="commute", annual_km=12_000, can_charge=True, mostly="mixed")
    cannot = recommend_profile(usage="commute", annual_km=12_000, can_charge=False, mostly="city")
    assert can.fuel == "electric"
    assert cannot.fuel != "electric"


def test_high_motorway_mileage_gets_a_diesel() -> None:
    profile = recommend_profile(usage="commute", annual_km=30_000, can_charge=False,
                                mostly="motorway")
    assert profile.fuel == "diesel"


def test_charging_at_home_does_not_override_motorway_distance() -> None:
    profile = recommend_profile(usage="travel", annual_km=35_000, can_charge=True,
                                mostly="motorway")
    assert profile.fuel == "diesel"


def test_every_recommendation_comes_with_its_reason() -> None:
    profile = recommend_profile(usage="work", annual_km=25_000, can_charge=False,
                                mostly="mixed", carries_cargo=True)
    assert len(profile.reasons) >= 3
    assert all(reason.endswith((".", "!")) for reason in profile.reasons)


def test_an_empty_answer_produces_questions_rather_than_a_guess() -> None:
    profile = recommend_profile()
    assert profile.body_types == []
    assert profile.fuel is None
    assert len(profile.open_questions) >= 3


def test_a_recommended_allowance_is_rounded_up_never_down() -> None:
    """Too small an allowance is a bill at the end of the contract."""
    assert nearest_tier(11_000) == 15_000
    assert nearest_tier(15_000) == 15_000
    assert nearest_tier(21_000) == 30_000
    assert nearest_tier(99_000) == 30_000


def test_the_tool_looks_up_a_previous_car_instead_of_guessing_it() -> None:
    result = advise_car_type(usage="commute", previous_car="Golf")
    assert result["previous_car"]["body_type"]
    assert result["next_question"]


def test_an_unknown_previous_car_is_simply_ignored() -> None:
    result = advise_car_type(usage="city", previous_car="Zaphod Beeblebrox 5000")
    assert "previous_car" not in result
    assert result["body_types"]


# --- partner dealers --------------------------------------------------------


def test_the_partner_network_is_a_selective_minority() -> None:
    stats = partners.partner_stats(get_db().query)
    assert 0 < stats["dealers"] < 2_000
    (total,) = get_db().query("SELECT count(*) AS n FROM ads WHERE seller_type = 'Dealer'")
    assert stats["listings"] < total["n"] / 2  # a badge everyone has is not a badge


def test_partner_cars_come_first_among_the_matches() -> None:
    cars = search_cars(max_monthly_rate=400, limit=5)["cars"]
    flags = [car["partner_dealer"] for car in cars]
    assert flags == sorted(flags, reverse=True)


def test_partner_priority_never_breaks_the_customer_s_own_filter() -> None:
    """A partner car still has to be under the budget to be shown."""
    result = search_cars(max_monthly_rate=250, body_type="estate", limit=5)
    for car in result["cars"]:
        assert car["monthly_rate_eur"] <= 250


def test_a_partner_shortlist_always_carries_the_disclosure() -> None:
    result = search_cars(max_monthly_rate=400, limit=3)
    if any(car["partner_dealer"] for car in result["cars"]):
        assert "does not change the price" in result["partner_disclosure"]


def test_private_sellers_are_never_partners() -> None:
    (row,) = get_db().query(
        f"SELECT count(*) AS n FROM ads WHERE seller_type <> 'Dealer' AND {partners.IS_PARTNER}"
    )
    assert row["n"] == 0


# --- buying instead of leasing ----------------------------------------------


def test_buying_lifts_the_leasing_rules() -> None:
    """Below the leasing price floor there are still cars to buy."""
    result = search_cars(mode="buy", max_price=3_000, limit=3)
    assert result["matches"] > 0
    assert all(car["monthly_rate_eur"] is None for car in result["cars"])
    assert "terms" not in result
    assert search_cars(max_price=3_000, limit=3)["matches"] == 0  # not leasable


def test_an_unknown_mode_explains_itself() -> None:
    with pytest.raises(ValueError, match="unknown mode"):
        search_cars(mode="rent")


# --- cosmetics and condition ------------------------------------------------


def test_colour_is_a_real_filter() -> None:
    for car in search_cars(color="red", limit=5)["cars"]:
        assert car["body_color"] == "Red"


def test_an_unknown_colour_explains_itself() -> None:
    with pytest.raises(ValueError, match="unknown color"):
        search_cars(color="taupe")


def test_condition_filters_are_applied_not_just_promised() -> None:
    for car in search_cars(no_accident=True, full_service_history=True,
                           max_previous_owners=1, limit=5)["cars"]:
        details = car_details(car["ref"])
        assert details["had_accident"] is not True
        assert details["full_service_history"] is True
        assert details["previous_owners"] <= 1


# --- the closing summary ----------------------------------------------------


@pytest.fixture(scope="module")
def chosen():
    return search_cars(max_monthly_rate=400, body_type="estate", no_accident=True,
                       limit=1)["cars"][0]


def test_the_summary_checks_the_car_rather_than_repeating_the_wish(chosen) -> None:
    summary = decision_summary(
        ref=chosen["ref"], used_for="family trips", body_type="estate",
        budget_monthly_eur=400, term_months=36, annual_km=15_000,
    )
    assert summary["choices"]["used_for"] == "family trips"
    assert summary["leasing"]["monthly_rate_eur"] <= 400
    assert any("estate" in reason for reason in summary["why_this_car"])


def test_the_summary_does_not_claim_a_preference_the_car_misses(chosen) -> None:
    summary = decision_summary(ref=chosen["ref"], color="violet", fuel="electric")
    assert not any("violet" in reason.lower() for reason in summary["why_this_car"])
    assert not any("electric" in reason.lower() for reason in summary["why_this_car"])


def test_the_summary_works_before_a_car_is_chosen() -> None:
    summary = decision_summary(used_for="commuting", budget_monthly_eur=250)
    assert summary["why_this_car"] == []
    assert summary["choices"]["budget_monthly_eur"] == 250
    assert len(summary["closing_options"]) == 3


def test_a_summary_ends_with_exactly_three_ways_out(chosen) -> None:
    options = closing_options()
    assert len(options["options"]) == 3
    assert sum(1 for option in options["options"] if option.get("default")) == 1
    (attach,) = [o for o in options["options"] if "include_agreement" in str(o.get("call"))]
    assert "explicitly asks" in attach["only_when"]


# --- a stated budget range is a range ---------------------------------------
#
# Reported from live use: asked for €800-1300 a month, the advisor offered
# €95-140 cars. There was no floor the model could reach, and the default sort
# is cheapest-first over every match, so a ceiling alone always bottomed out.


def test_a_range_returns_only_cars_inside_it() -> None:
    result = search_cars(min_monthly_rate=800, max_monthly_rate=1300, limit=5)
    assert result["matches"] > 0
    assert result["cars"]
    for car in result["cars"]:
        assert 800 <= car["monthly_rate_eur"] <= 1300


def test_a_range_is_spread_across_itself_rather_than_piled_on_the_floor() -> None:
    """The complaint was cars at the wrong end; three cars at €801 is the same bug."""
    rates = [
        car["monthly_rate_eur"]
        for car in search_cars(min_monthly_rate=800, max_monthly_rate=1300, limit=3)["cars"]
    ]
    assert len(rates) == 3
    assert rates == sorted(rates)
    # Each pick comes from its own third of the band, so they cannot cluster.
    assert rates[-1] - rates[0] > 150, rates
    assert rates[-1] > 1000, rates


def test_a_bare_ceiling_still_means_cheapest_first() -> None:
    """The old behaviour is correct when a ceiling is all the customer gave."""
    result = search_cars(max_monthly_rate=1300, limit=3)
    rates = [car["monthly_rate_eur"] for car in result["cars"]]
    assert rates == sorted(rates)
    assert "ranked" not in result  # nothing to explain: nothing was spread
    assert min(rates) < 300


def test_the_applied_budget_comes_back_so_it_can_be_said_out_loud() -> None:
    result = search_cars(min_monthly_rate=500, max_monthly_rate=700, limit=1)
    assert result["budget"] == {"min_monthly_rate": 500, "max_monthly_rate": 700}
    assert "spread" in result["ranked"].lower()


def test_a_floor_above_the_ceiling_is_a_question_not_an_empty_result() -> None:
    with pytest.raises(ValueError, match="above the highest"):
        search_cars(min_monthly_rate=1300, max_monthly_rate=800)
    with pytest.raises(ValueError, match="above the highest"):
        search_cars(min_price=40_000, max_price=10_000)


def test_an_impossible_band_names_the_band_it_searched() -> None:
    result = search_cars(min_monthly_rate=9_000, max_monthly_rate=9_500, body_type="compact")
    assert result["matches"] == 0
    assert "9" in result["hint"]  # the numbers they gave, not "relax something"
    assert "outside the range" in result["hint"]


def test_buying_says_it_ignored_the_monthly_floor() -> None:
    result = search_cars(mode="buy", min_monthly_rate=800, max_price=20_000, limit=1)
    assert "does not apply when buying" in result["ignored"]


# --- advice is personal, and stays a suggestion ------------------------------


def test_nothing_is_recommended_before_anything_is_asked() -> None:
    """The empty call must produce questions, not a screenful of defaults."""
    result = advise_car_type()
    assert not _has_recommendation(result)
    assert result["because"] == []
    assert result["annual_km"] is None  # no allowance nobody chose
    assert result["open_questions"]


def test_a_recommendation_names_the_circumstances_it_came_from() -> None:
    result = advise_car_type(usage="family", passengers=5, annual_km=20_000,
                             can_charge=False, mostly="motorway")
    assert _has_recommendation(result)
    assert result["is_personal"] is True
    because = " | ".join(result["because"])
    assert "5 of you" in because
    assert "motorway" in because
    assert "charger" in because


def test_a_hobby_shapes_the_car_and_says_why() -> None:
    plain = advise_car_type(usage="commute", annual_km=12_000)
    cycles = advise_car_type(usage="commute", annual_km=12_000, hobbies="I cycle every weekend")
    assert cycles["body_types"][0] == "estate"  # promoted ahead of the compact
    assert cycles["body_types"] != plain["body_types"]
    assert any("bike" in reason.lower() for reason in cycles["reasons"])
    assert "you cycle" in cycles["because"]


def test_a_hobby_never_outranks_a_seat_count() -> None:
    """Six people still need six seats, whatever they do at the weekend."""
    result = advise_car_type(usage="family", passengers=6, hobbies="cycling and skiing")
    assert result["body_types"][0] == "van"
    assert result["min_seats"] == 7


def test_an_unrecognised_hobby_is_ignored_rather_than_rejected() -> None:
    result = advise_car_type(usage="city", hobbies="competitive yodelling")
    assert result["body_types"]  # still advises
    assert not any("yodel" in b.lower() for b in result["body_types"])


def test_what_we_suggested_is_never_reported_as_what_they_chose(chosen) -> None:
    summary = decision_summary(
        ref=chosen["ref"], used_for="commuting",
        suggested_body_type="estate", suggested_fuel="diesel",
    )
    assert summary["suggested"] == {"body_type": "estate", "fuel": "diesel"}
    assert "body_type" not in summary["choices"]
    assert "fuel" not in summary["choices"]
    # And it is not offered as evidence that the car fits them.
    assert not any("estate you asked for" in r for r in summary["why_this_car"])


def test_a_rate_below_the_range_is_not_called_inside_their_budget(chosen) -> None:
    """The €190 car is not "inside the €800 to €1300 you wanted to spend"."""
    summary = decision_summary(
        ref=chosen["ref"], min_budget_monthly_eur=800, budget_monthly_eur=1300,
        term_months=36, annual_km=15_000,
    )
    assert summary["leasing"]["monthly_rate_eur"] < 800  # the fixture is a cheap car
    assert not any("you wanted to spend" in reason for reason in summary["why_this_car"])


def test_a_rate_inside_the_range_says_both_ends_of_it() -> None:
    car = search_cars(min_monthly_rate=800, max_monthly_rate=1300, limit=1)["cars"][0]
    summary = decision_summary(
        ref=car["ref"], min_budget_monthly_eur=800, budget_monthly_eur=1300,
        term_months=36, annual_km=15_000,
    )
    reason = summary["why_this_car"][0]
    assert "800" in reason and "300" in reason
    assert "you wanted to spend" in reason
