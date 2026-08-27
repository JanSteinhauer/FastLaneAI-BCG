"""What the visitor sees while the agent talks.

A voice agent that only talks makes the listener hold six numbers in their head.
Every tool that produces something concrete — a shortlist, a spec, a rate, a
sent email — also pushes a card to the web page over the LiveKit data channel
(topic "ui"), so the customer can *see* the shortlist while hearing the advice.

Payload shapes understood by frontend/src/main.jsx:

    {"type": "cars",  "cars": [...]}    listing cards
    {"type": "quote", ...}              a title + rows + footnote panel
    {"type": "sent",  ...}              email confirmation
    {"type": "text",  "text": "..."}    a plain bubble

Five of the payloads below (quote, advice, deal, options, explanation, summary)
share the "quote" shape rather than inventing new ones: the frontend ships as a
pre-built bundle, and a label/value panel is exactly what all of them are. One
renderer, several uses, no rebuild.

Drawing is best-effort: if the page is gone, the conversation continues.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from used_car_advisor.state import RunContext_T

logger = logging.getLogger("used-car-advisor.ui")


async def push(context: RunContext_T, payload: dict[str, Any]) -> None:
    """Show content in the web frontend while the agent keeps talking."""
    userdata = context.userdata
    if userdata.ctx is None or userdata.ctx.room is None:
        return
    try:
        await userdata.ctx.room.local_participant.send_text(
            json.dumps(payload), topic="ui"
        )
    except Exception:
        logger.debug("push_to_frontend failed", exc_info=True)


def _eur(value: float | None, decimals: int = 0) -> str:
    if value is None:
        return "—"
    return f"€{value:,.{decimals}f}".replace(",", " ")


def _rating(card: dict[str, Any]) -> str:
    """The price verdict, in one line — always shown, asked for or not.

    "/5" is appended only when there is a score behind it. A car whose peer
    group never filled still gets its line ("No comparison"), because a missing
    rating has to read as "I cannot tell" rather than as a line we dropped —
    and never as 0.0 out of 5, which would read as the worst price on the lot.
    """
    label = card.get("deal_label")
    if not label:
        return ""
    score = card.get("deal_score")
    return f"{label} {score}/5" if score is not None else str(label)


def cars_payload(cars: list[dict[str, Any]], terms: dict[str, Any] | None = None) -> dict:
    """Listing cards — monthly rate first, because that is what customers compare."""
    return {
        "type": "cars",
        "subtitle": (
            f"{terms['term_months']} months · {terms['annual_km']:,} km/year".replace(",", " ")
            if terms
            else None
        ),
        "cars": [
            {
                "ref": car["ref"],
                "title": car["title"],
                "price": (
                    f"{_eur(car['monthly_rate_eur'])} / month"
                    if car.get("monthly_rate_eur")
                    else _eur(car.get("price_eur"))
                ),
                "sub": " · ".join(
                    x
                    for x in (
                        _eur(car.get("price_eur")) + " listing price",
                        _rating(car) or None,
                    )
                    if x
                ),
                "year": car.get("year"),
                "mileage_km": car.get("mileage_km"),
                "fuel": car.get("fuel"),
                "meta2": " · ".join(
                    str(x)
                    for x in (
                        f"{car['power_hp']} hp" if car.get("power_hp") else None,
                        car.get("transmission"),
                        car.get("city"),
                        # The commercial disclosure belongs on the card itself,
                        # not only in whatever the advisor happens to say.
                        "★ Partner dealer" if car.get("partner_dealer") else None,
                    )
                    if x
                ),
            }
            for car in cars
        ],
    }


def _panel(
    title: str, headline: str, note: str, rows: list[list[str]], footnote: str
) -> dict:
    """The label/value panel the quote card renders — reused by everything below."""
    return {
        "type": "quote",
        "title": title,
        "headline": headline,
        "headline_note": note,
        "rows": rows,
        "footnote": footnote,
    }


def quote_payload(quote: dict[str, Any]) -> dict:
    """The leasing agreement, as the customer will see it in the email."""
    breakdown = quote.get("breakdown", {})
    return {
        "type": "quote",
        "title": quote.get("car", ""),
        "headline": _eur(quote.get("monthly_rate_eur"), 2),
        "headline_note": "per month, gross",
        "rows": [
            # First row: the moment a customer is asked to accept a number is
            # the moment they most want to know the price is fair.
            ["Price rating", _rating(quote) or "—"],
            ["Term", f"{quote.get('term_months')} months"],
            ["Mileage", f"{quote.get('annual_km', 0):,} km / year".replace(",", " ")],
            ["Down payment", _eur(quote.get("down_payment_eur"))],
            ["Depreciation", f"{_eur(breakdown.get('depreciation_eur'), 2)} / month"],
            ["Finance charge", f"{_eur(breakdown.get('finance_eur'), 2)} / month"],
            ["Nominal annual rate", f"{breakdown.get('apr_pct')} %"],
            ["Residual value", _eur(breakdown.get("residual_value_eur"))],
            ["Total over term", _eur(quote.get("total_cost_eur"))],
        ],
        "footnote": "Indicative offer · incl. VAT · not a credit agreement",
    }


def sent_payload(result: dict[str, Any]) -> dict:
    """Email confirmation card."""
    return {
        "type": "sent",
        "title": "Offer sent",
        "recipient": result.get("recipient", ""),
        "reference": result.get("reference", ""),
        "note": "Car summary and leasing agreement are in your inbox.",
    }


def text_payload(text: str) -> dict:
    return {"type": "text", "text": text}


def advice_payload(profile: dict[str, Any]) -> dict:
    """Our recommendation for THIS person, and the circumstances behind it.

    Two rules hold here. Every row is something actually derived from what the
    customer said — an empty profile draws nothing at all (the caller checks),
    and a default nobody chose is not a row. And the panel says whose idea this
    is: it leads with *their* circumstances, so the advice reads as personal
    rather than as a set of decisions already taken on their behalf.
    """
    body_types = profile.get("body_types") or []
    because = profile.get("because") or []
    rows: list[list[str]] = []
    if because:
        rows.append(["Because you told me", ", ".join(str(b) for b in because)])
    if body_types:
        rows.append(["Body type", ", ".join(body_types)])
    if profile.get("fuel"):
        rows.append(["Fuel", str(profile["fuel"])])
    if profile.get("transmission"):
        rows.append(["Transmission", str(profile["transmission"])])
    if profile.get("min_seats"):
        rows.append(["Seats", f"at least {profile['min_seats']}"])
    # Only when they named a mileage. This row used to be drawn unconditionally
    # from a 15 000 km default, which put an allowance on their screen that
    # nobody had agreed to.
    if profile.get("annual_km"):
        rows.append(
            ["Mileage allowance", f"{profile['annual_km']:,} km / year".replace(",", " ")]
        )
    rows += [["Why", reason] for reason in (profile.get("reasons") or [])]
    first = body_types[0] if body_types else ""
    return _panel(
        "My recommendation for you",
        # Not .title(): that turned "Let's narrow it down" into "Let'S Narrow
        # It Down" and "SUV" into "Suv".
        (first[:1].upper() + first[1:]) if first else "A place to start",
        "personal — based on what you told me",
        rows,
        "A suggestion, not a decision — say so if it does not sound like you.",
    )


def deal_payload(deal: dict[str, Any]) -> dict:
    """The deal score: where this price sits among comparable listings."""
    rows = [["Listing price", _eur(deal.get("price_eur"))]]
    if deal.get("comparables"):
        rows += [
            ["Comparable cars", str(deal["comparables"])],
            ["Peer group", str(deal.get("peer_group", ""))],
            ["Average price", _eur(deal.get("average_price_eur"))],
            ["Median price", _eur(deal.get("median_price_eur"))],
            ["Difference", f"{deal.get('difference_pct', 0):+.1f} %"],
        ]
    return _panel(
        str(deal.get("car", "")),
        f"{deal.get('score', 0)} / 5",
        str(deal.get("label", "")),
        rows,
        "Calculated from the listings snapshot — not an opinion.",
    )


def options_payload(options: dict[str, Any]) -> dict:
    """The buckets a customer may choose from."""
    rows = [
        ["Terms", ", ".join(f"{t} months" for t in options.get("term_months", []))],
        [
            "Mileage tiers",
            ", ".join(f"{k:,} km".replace(",", " ") for k in options.get("annual_km", [])),
        ],
        ["Down payment", f"up to {options.get('max_down_payment_share', 0):.0%} of the price"],
        ["Minimum car price", _eur(options.get("min_price_eur"))],
    ]
    rows += [
        [f"{term} months", str(text)]
        for term, text in (options.get("term_trade_offs") or {}).items()
    ]
    return _panel(
        "What you can choose",
        "Leasing terms",
        "fixed buckets — we cannot price anything in between",
        rows,
        str(options.get("contract_type", "")),
    )


def explanation_payload(explanation: dict[str, Any]) -> dict:
    """The full derivation of the monthly rate."""
    rows: list[list[str] | None] = [
        [f"Step {step['step']}", f"{step['what']} — {step['formula']}"]
        for step in explanation.get("steps", [])
    ]
    worked = explanation.get("worked_example") or {}
    rows += [
        ["Listing price", worked["listing_price"]] if worked.get("listing_price") else None,
        ["Residual value", worked["projected_residual_value"]]
        if worked.get("projected_residual_value")
        else None,
        ["Depreciation", worked["depreciation_per_month"]]
        if worked.get("depreciation_per_month")
        else None,
        ["Finance charge", worked["finance_per_month"]]
        if worked.get("finance_per_month")
        else None,
        ["Monthly rate", worked["monthly_rate"]] if worked.get("monthly_rate") else None,
        ["Not included", ", ".join(explanation.get("not_included", []))],
    ]
    return _panel(
        "How your rate is calculated",
        "Depreciation + finance",
        "nothing else is in the rate",
        [row for row in rows if row],
        str(explanation.get("no_hidden_fees", "")),
    )


def summary_payload(summary: dict[str, Any]) -> dict:
    """The closing summary: their choices, this car, and why the two match."""
    car = summary.get("car") or {}
    leasing = summary.get("leasing") or {}
    choices = summary.get("choices") or {}
    low, high = choices.get("min_budget_monthly_eur"), choices.get("budget_monthly_eur")
    rows: list[list[str]] = []
    for key, value in choices.items():
        if key == "min_budget_monthly_eur":
            continue  # folded into the single budget row below
        if key == "budget_monthly_eur":
            rows.append(["Budget", _budget_text(low, high)])
            continue
        rows.append([_label(key), _value(value)])
    if low is not None and high is None:  # a floor on its own still gets said
        rows.append(["Budget", _budget_text(low, None)])
    # What we suggested is listed apart from what they chose, and labelled as
    # ours. Folding the two together is how a summary ends up telling someone
    # they asked for an estate when all they did was not disagree with one.
    rows += [
        [f"I suggested ({_label(key)})", _value(value)]
        for key, value in (summary.get("suggested") or {}).items()
    ]
    if leasing.get("monthly_rate_eur"):
        rows.append(["Your rate", f"{_eur(leasing['monthly_rate_eur'], 2)} / month"])
    # The verdict belongs on the closing card too — this is the last thing they
    # see before saying yes.
    if rating := _rating(summary.get("deal") or {}):
        rows.append(["Price rating", rating])
    rows += [["Why this car", reason] for reason in (summary.get("why_this_car") or [])]
    return _panel(
        car.get("title", "Your choice"),
        _eur(leasing.get("monthly_rate_eur") or car.get("price_eur"), 2),
        "per month, gross" if leasing.get("monthly_rate_eur") else "purchase price",
        rows,
        "Say the word and I email this to you.",
    )


#: The keys the generic rule below mangles — "annual_km" came out as "Annual".
_LABELS = {
    "annual_km": "Annual mileage",
    "max_mileage_km": "Maximum mileage",
    "down_payment_eur": "Down payment",
}


def _label(key: str) -> str:
    """'budget_monthly_eur' -> 'Budget monthly'; a few need saying properly."""
    if key in _LABELS:
        return _LABELS[key]
    return key.replace("_eur", "").replace("_km", "").replace("_", " ").capitalize()


def _budget_text(low: float | None, high: float | None) -> str:
    """Their budget as one line, however many ends of it they gave us."""
    if low is not None and high is not None:
        return f"{_eur(low)} to {_eur(high)} / month"
    if high is not None:
        return f"up to {_eur(high)} / month"
    return f"from {_eur(low)} / month"


def _value(value: Any) -> str:
    return f"{value:,}".replace(",", " ") if isinstance(value, int | float) else str(value)
