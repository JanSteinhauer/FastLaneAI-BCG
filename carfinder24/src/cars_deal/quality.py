"""Deal quality: what a car like this costs, and where this one sits.

"Is that a good price?" is the question every used-car buyer actually asks, and
it is the one an LLM must never answer from feel. So the verdict is arithmetic:

1. build a **peer group** — the same car, near enough: same make and model,
   same vehicle and body type, similar age, similar odometer;
2. take the peer group's **average price**;
3. score this listing against it on a fixed **0.0 – 5.0** scale, where 5.0 is a
   very good deal, and map the score to a plain-English label
   (*Very good price* / *Good price* / *Fair price* / …).

Determinism is the whole point: same snapshot, same listing, same number, every
time — so the advisor can say it out loud and the email can repeat it.

The peer definition widens in fixed steps (`PEER_LEVELS`) until it holds at
least `MIN_PEERS` cars. A rare model that never gets there scores nothing at
all rather than being judged against three coincidences; "I cannot tell" is an
allowed answer here.

The comparison is between *listing prices*, not leasing rates: the rate is
derived from the price, so a good price is a good rate.
"""

from __future__ import annotations

from dataclasses import dataclass

# -- scale -------------------------------------------------------------------
# 20% below the peer average is as good as this scale goes; 20% above is as bad.
# The mapping in between is linear, so the midpoint (2.5) is exactly the average
# price — a genuinely fair one.
FULL_DISCOUNT = 0.20
MIN_PEERS = 5

#: score threshold -> (German label, English gloss). Checked top down.
LABELS: tuple[tuple[float, str, str], ...] = (
    (4.0, "Very good price", "very good price"),
    (3.0, "Good price", "good price"),
    (2.0, "Fair price", "fair price"),
    (1.0, "Increased price", "above the going rate"),
    (0.0, "High price", "expensive for what it is"),
)


@dataclass(frozen=True)
class PeerLevel:
    """One rung of the widening ladder of "cars like this one"."""

    name: str
    description: str
    where: str  # SQL predicate over `ads`, using the $params of peer_params()


# Tried in order; the first level with at least MIN_PEERS cars wins. Every level
# keeps make and model fixed — a Golf is never priced against a Passat.
PEER_LEVELS: tuple[PeerLevel, ...] = (
    PeerLevel(
        "close",
        "same model and body type, within 2 years and 20,000 km",
        """make = $make AND model = $model
           AND vehicle_type IS NOT DISTINCT FROM $vehicle_type
           AND body_type IS NOT DISTINCT FROM $body_type
           AND abs(date_part('year', registration_date) - $year) <= 2
           AND abs(mileage_km - $mileage_km) <= 20000""",
    ),
    PeerLevel(
        "wider",
        "same model, within 3 years and 40,000 km",
        """make = $make AND model = $model
           AND vehicle_type IS NOT DISTINCT FROM $vehicle_type
           AND abs(date_part('year', registration_date) - $year) <= 3
           AND abs(mileage_km - $mileage_km) <= 40000""",
    ),
    PeerLevel(
        "model",
        "every listing of this model in the snapshot",
        "make = $make AND model = $model",
    ),
)


@dataclass(frozen=True)
class PeerGroup:
    """The cars this one was judged against."""

    level: str
    description: str
    n: int
    average_price: float
    median_price: float
    min_price: int
    max_price: int


@dataclass(frozen=True)
class DealScore:
    """Where a listing sits against its peers — the whole verdict."""

    score: float  # 0.0 (expensive) .. 5.0 (very good deal)
    label: str  # German, as buyers know it
    label_en: str
    difference_pct: float  # vs. the peer average; negative is cheaper
    peers: PeerGroup | None
    explanation: str  # one sentence, safe to read out loud


def label_for(score: float) -> tuple[str, str]:
    """The German label and its English gloss for a 0.0-5.0 score."""
    for threshold, german, english in LABELS:
        if score >= threshold:
            return german, english
    return LABELS[-1][1], LABELS[-1][2]


def score_offer(price: int, peers: PeerGroup | None) -> DealScore:
    """Rank one listing against its peer group. Pure arithmetic, no opinions."""
    if peers is None or peers.n < MIN_PEERS or not peers.average_price:
        return DealScore(
            score=0.0,
            label="No comparison",
            label_en="not enough comparable cars",
            difference_pct=0.0,
            peers=peers,
            explanation=(
                "There are too few comparable cars in the snapshot to judge this "
                "price, so I would rather not put a number on it."
            ),
        )

    delta = (price - peers.average_price) / peers.average_price
    score = round(min(5.0, max(0.0, 2.5 * (1 - delta / FULL_DISCOUNT))), 1)
    german, english = label_for(score)
    average = f"€{peers.average_price:,.0f}".replace(",", " ")
    direction = (
        f"{abs(delta):.0%} below" if delta < -0.005
        else f"{abs(delta):.0%} above" if delta > 0.005
        else "right on"
    )
    return DealScore(
        score=score,
        label=german,
        label_en=english,
        difference_pct=round(delta * 100, 1),
        peers=peers,
        explanation=(
            f"{german} — {english}. This car is {direction} the {average} "
            f"average of {peers.n} comparable listings ({peers.description}). "
            f"That scores {score} out of 5."
        ),
    )


def peer_params(row: dict) -> dict:
    """The $params every level in PEER_LEVELS binds against."""
    date = row.get("registration_date")
    return {
        "id": row["id"],
        "make": row["make"],
        "model": row["model"],
        "vehicle_type": row.get("vehicle_type"),
        "body_type": row.get("body_type"),
        "year": date.year if date else None,
        "mileage_km": row.get("mileage_km"),
    }


def peer_query(level: PeerLevel, row: dict) -> tuple[str, dict]:
    """SQL + bound params for one peer level, ready for CarsDB.query().

    Only the parameters the level actually mentions are bound — the widest
    level ignores age and mileage, and DuckDB rejects params it was not asked
    for.
    """
    sql = _peer_sql(level)
    params = {k: v for k, v in peer_params(row).items() if f"${k}" in sql}
    return sql, params


def _peer_sql(level: PeerLevel) -> str:
    """Aggregate query for one peer level; bind it with peer_params()."""
    return f"""
        SELECT count(*) AS n,
               avg(price) AS average_price,
               median(price) AS median_price,
               min(price) AS min_price,
               max(price) AS max_price
        FROM ads
        WHERE id <> $id AND price IS NOT NULL
          AND registration_date IS NOT NULL AND mileage_km IS NOT NULL
          AND ({level.where})
    """
