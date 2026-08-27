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
from cars_mcp.server import get_db, price_check, search_cars


def peers(average: float, n: int = 40) -> PeerGroup:
    return PeerGroup(
        level="close", description="test peers", n=n, average_price=average,
        median_price=average, min_price=int(average * 0.6), max_price=int(average * 1.4),
    )


# --- the scale --------------------------------------------------------------


def test_the_average_price_scores_exactly_in_the_middle() -> None:
    deal = score_offer(20_000, peers(20_000))
    assert deal.score == 2.5
    assert deal.label == "Fairer Preis"
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
    [(5.0, "Sehr guter Preis"), (4.0, "Sehr guter Preis"), (3.5, "Guter Preis"),
     (2.5, "Fairer Preis"), (1.5, "Erhöhter Preis"), (0.0, "Hoher Preis")],
)
def test_scores_map_to_the_labels_german_buyers_know(score, label) -> None:
    assert label_for(score)[0] == label


def test_the_verdict_says_the_number_and_what_it_was_compared_against() -> None:
    deal = score_offer(17_000, peers(20_000, n=42))
    assert "42 comparable listings" in deal.explanation
    assert str(deal.score) in deal.explanation
    assert deal.label in deal.explanation


# --- refusing to judge ------------------------------------------------------


def test_too_few_comparable_cars_means_no_verdict() -> None:
    deal = score_offer(20_000, peers(20_000, n=MIN_PEERS - 1))
    assert deal.label == "Kein Vergleich"
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
