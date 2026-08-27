"""The deal score: same car, same number, every time — and the right number.

"Is this a good price?" is answered by arithmetic against a peer group, so
these tests pin down the arithmetic (monotonic, bounded, labelled) and the peer
group (same model, widened in fixed steps, never judged on three coincidences).
"""

from __future__ import annotations

import pytest

from cars_deal.quality import (
    FULL_DISCOUNT,
    MIN_PEERS,
    PEER_LEVELS,
    PeerGroup,
    label_for,
    peer_query,
    score_offer,
)
from cars_mcp.server import (
    car_details,
    decision_summary,
    get_db,
    leasing_quote,
    price_check,
    search_cars,
)
from used_car_advisor.ui import _rating


def peers(average: float, n: int = 40) -> PeerGroup:
    return PeerGroup(
        level="close", description="test peers", n=n, average_price=average,
        median_price=average, min_price=int(average * 0.6), max_price=int(average * 1.4),
    )


# --- the scale --------------------------------------------------------------


def test_the_average_price_scores_exactly_in_the_middle() -> None:
    deal = score_offer(20_000, peers(20_000))
    assert deal.score == 2.5
    assert deal.label == "Fair price"
    assert deal.difference_pct == 0.0


def test_cheaper_always_scores_higher() -> None:
    scores = [score_offer(price, peers(20_000)).score
              for price in (26_000, 22_000, 20_000, 18_000, 14_000)]
    assert scores == sorted(scores)
    assert len(set(scores)) == len(scores)  # no plateau in the useful range


def test_the_scale_is_bounded_at_both_ends() -> None:
    assert score_offer(1, peers(20_000)).score == 5.0
    assert score_offer(10_000_000, peers(20_000)).score == 0.0


def test_a_full_discount_earns_full_marks() -> None:
    at_the_top = int(20_000 * (1 - FULL_DISCOUNT))
    assert score_offer(at_the_top, peers(20_000)).score == 5.0
    assert score_offer(at_the_top + 500, peers(20_000)).score < 5.0


@pytest.mark.parametrize(
    ("score", "label"),
    [(5.0, "Very good price"), (4.0, "Very good price"), (3.5, "Good price"),
     (2.5, "Fair price"), (1.5, "Increased price"), (0.0, "High price")],
)
def test_scores_map_to_the_labels_a_buyer_understands(score, label) -> None:
    """Every label a customer can hear is English — see the product language rule."""
    assert label_for(score)[0] == label


def test_the_verdict_says_the_number_and_what_it_was_compared_against() -> None:
    deal = score_offer(17_000, peers(20_000, n=42))
    assert "42 comparable listings" in deal.explanation
    assert str(deal.score) in deal.explanation
    assert deal.label in deal.explanation


# --- refusing to judge ------------------------------------------------------


def test_too_few_comparable_cars_means_no_verdict() -> None:
    deal = score_offer(20_000, peers(20_000, n=MIN_PEERS - 1))
    assert deal.label == "No comparison"
    assert "too few" in deal.explanation


def test_no_peer_group_at_all_means_no_verdict() -> None:
    assert score_offer(20_000, None).peers is None


# --- against the real snapshot ----------------------------------------------


@pytest.fixture(scope="module")
def sample_rows():
    return get_db().query(
        """
        SELECT * FROM ads
        WHERE price IS NOT NULL AND mileage_km IS NOT NULL
          AND registration_date IS NOT NULL
        USING SAMPLE 15 ROWS (reservoir, 11)
        """
    )


def test_peer_levels_only_ever_widen(sample_rows) -> None:
    """Each rung must find at least as many cars as the one before it."""
    for row in sample_rows:
        counts = []
        for level in PEER_LEVELS:
            sql, params = peer_query(level, row)
            counts.append(get_db().query(sql, params)[0]["n"])
        assert counts == sorted(counts), f"{row['make']} {row['model']}: {counts}"


def test_a_peer_is_never_a_different_model(sample_rows) -> None:
    for row in sample_rows[:5]:
        sql, params = peer_query(PEER_LEVELS[-1], row)
        (stats,) = get_db().query(
            sql.replace(
                "count(*) AS n,", "count(*) AS n, count(DISTINCT model) AS models,"
            ),
            params,
        )
        assert stats["n"] == 0 or stats["models"] == 1


def test_the_same_listing_always_scores_the_same() -> None:
    ref = search_cars(max_monthly_rate=300, limit=1)["cars"][0]["ref"]
    first, second = price_check(ref), price_check(ref)
    assert first == second
    assert 0.0 <= first["score"] <= 5.0


def test_the_verdict_carries_its_evidence() -> None:
    ref = search_cars(max_monthly_rate=400, make="BMW", limit=1)["cars"][0]["ref"]
    result = price_check(ref)
    assert result["comparables"] >= MIN_PEERS
    assert result["average_price_eur"] > 0
    assert result["range_eur"][0] <= result["average_price_eur"] <= result["range_eur"][1]
    assert result["label"] in result["verdict"]


def test_search_results_carry_the_same_score_price_check_gives() -> None:
    """The badge on the card and the verdict on request cannot disagree."""
    for car in search_cars(max_monthly_rate=350, limit=3)["cars"]:
        if "deal_score" in car:
            assert price_check(car["ref"])["score"] == car["deal_score"]


# --- the rating is always on screen -----------------------------------------
#
# It used to ride only on search cards. Asking "tell me more about the second
# one" called car_details, which redrew the card WITHOUT the rating it just
# had — the rating disappeared exactly when the customer leaned in.


def test_car_details_carries_the_rating_too() -> None:
    ref = search_cars(max_monthly_rate=400, limit=1)["cars"][0]["ref"]
    details = car_details(ref)
    assert details["deal_label"]
    assert details["deal_score"] == price_check(ref)["score"]


def test_the_quote_carries_the_rating_next_to_the_rate() -> None:
    ref = search_cars(max_monthly_rate=400, limit=1)["cars"][0]["ref"]
    quote = leasing_quote(ref, 36, 15_000)
    assert quote["deal_label"] == price_check(ref)["label"]
    assert quote["deal_score"] == price_check(ref)["score"]


def test_the_closing_summary_carries_the_rating() -> None:
    ref = search_cars(max_monthly_rate=400, limit=1)["cars"][0]["ref"]
    summary = decision_summary(ref=ref, term_months=36, annual_km=15_000)
    assert summary["deal"]["deal_label"] == price_check(ref)["label"]


def test_every_surface_reads_the_same_number() -> None:
    """One listing, four surfaces, one verdict — they cannot drift apart."""
    ref = search_cars(max_monthly_rate=500, limit=1)["cars"][0]["ref"]
    card = search_cars(max_monthly_rate=500, limit=1)["cars"][0]
    verdicts = {
        card["deal_label"],
        car_details(ref)["deal_label"],
        leasing_quote(ref, 36, 15_000)["deal_label"],
        decision_summary(ref=ref, term_months=36, annual_km=15_000)["deal"]["deal_label"],
        price_check(ref)["label"],
    }
    assert len(verdicts) == 1, verdicts


def test_an_unratable_car_gets_a_line_rather_than_a_gap() -> None:
    """"I cannot tell" is an allowed answer; a missing line is not."""
    unratable = _card_without_peers()
    assert unratable["deal_label"] == "No comparison"
    # Never 0.0: that would read as the worst price on the lot.
    assert unratable["deal_score"] is None
    assert _rating(unratable) == "No comparison"


def _card_without_peers() -> dict:
    from cars_mcp.server import _card

    return _card(
        {"id": "0" * 36, "make": "Rare", "model": "Thing", "price": 20_000,
         "mileage_km": 50_000, "registration_date": None, "monthly_rate": None},
        score_offer(20_000, None),
    )
