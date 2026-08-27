"""What the visitor sees while the agent talks.

A voice agent that only talks makes the listener hold six numbers in their head.
Every tool that produces something concrete — a shortlist, a spec, a rate, a
sent email — also pushes a card to the web page over the LiveKit data channel
(topic "ui"), so the customer can *see* the shortlist while hearing the advice.

Payload shapes understood by frontend/src/main.jsx:

    {"type": "cars",    "cars": [...]}  listing cards
    {"type": "detail",  ...}            one car's full spec
    {"type": "verdict", ...}            the price check
    {"type": "quote",   ...}            the leasing agreement card
    {"type": "sent",    ...}            email confirmation
    {"type": "text",    "text": "..."}  a plain bubble

Anything else is rendered as a labelled card, never as raw JSON — the page is
in front of a customer, so an unrecognised payload has to degrade into
something readable rather than into a debug dump.

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


async def push_progress(context: RunContext_T, payload: dict[str, Any]) -> None:
    """Update the progress strip.

    Sent on its own topic ("progress") rather than "ui": the strip lives above
    the conversation and must not replace whatever card the customer is looking
    at. Best-effort, like every other draw.
    """
    userdata = context.userdata
    if userdata.ctx is None or userdata.ctx.room is None:
        return
    try:
        await userdata.ctx.room.local_participant.send_text(
            json.dumps(payload), topic="progress"
        )
    except Exception:
        logger.debug("push_progress failed", exc_info=True)


def _eur(value: float | int | None, decimals: int = 0) -> str:
    if value is None:
        return "—"
    return f"€{value:,.{decimals}f}".replace(",", " ")


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
                "sub": _eur(car.get("price_eur")) + " listing price",
                "year": car.get("year"),
                "mileage_km": car.get("mileage_km"),
                "fuel": car.get("fuel"),
                "meta2": " · ".join(
                    str(x)
                    for x in (
                        f"{car['power_hp']} hp" if car.get("power_hp") else None,
                        car.get("transmission"),
                        car.get("city"),
                    )
                    if x
                ),
            }
            for car in cars
        ],
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


def _km(value: Any) -> str | None:
    return f"{value:,} km".replace(",", " ") if isinstance(value, (int, float)) else None


def detail_payload(car: dict[str, Any]) -> dict:
    """One car's full specification — what the customer asked to hear about.

    Values are formatted here rather than in the browser, so the page stays a
    dumb renderer and the wording matches what the advisor says out loud.
    """
    specs: list[list[str]] = []

    def spec(label: str, value: Any, suffix: str = "") -> None:
        if value is None or value == "":
            return
        text = f"{value:,}".replace(",", " ") if isinstance(value, int) else str(value)
        specs.append([label, f"{text}{suffix}"])

    # str(): a year is a label, not a quantity — "2021", never "2 021".
    spec("Registered", str(car["year"]) if car.get("year") else None)
    spec("Mileage", _km(car.get("mileage_km")))
    spec("Power", car.get("power_hp"), " hp")
    spec("Fuel", car.get("fuel"))
    spec("Transmission", car.get("transmission"))
    spec("Drive", car.get("drive_train"))
    spec("Body", car.get("body_type"))
    spec("Seats", car.get("seats"))
    spec("Doors", car.get("doors"))
    spec("Colour", car.get("body_color"))
    spec("Consumption", car.get("consumption_l_100km"), " l/100 km")
    spec("CO\u2082", car.get("co2_g_km"), " g/km")
    spec("Electric range", _km(car.get("electric_range_km")))
    spec("Previous owners", car.get("previous_owners"))

    flags = [
        label
        for label, ok in (
            ("Accident-free", car.get("had_accident") is False),
            ("Full service history", bool(car.get("full_service_history"))),
            ("Non-smoking", bool(car.get("non_smoking"))),
        )
        if ok
    ]

    return {
        "type": "detail",
        "title": car.get("title", ""),
        "headline": _eur(car.get("price_eur")),
        "headline_note": "listing price",
        "where": " \u00b7 ".join(
            x for x in (car.get("city"), car.get("seller")) if x
        ),
        "specs": specs,
        "flags": flags,
        "equipment": [e for e in (car.get("equipment") or []) if e][:8],
        "description": car.get("seller_description") or "",
    }


def verdict_payload(result: dict[str, Any]) -> dict:
    """The price check — evidence, not an opinion."""
    delta = result.get("difference_pct")
    rows = []
    if result.get("median_price_eur"):
        rows = [
            ["This car", _eur(result.get("price_eur"))],
            ["Median of comparables", _eur(result.get("median_price_eur"))],
            ["Comparable listings", str(result.get("comparables", 0))],
        ]
    return {
        "type": "verdict",
        "headline": f"{delta:+.1f}%" if isinstance(delta, (int, float)) else "\u2014",
        "tone": (
            "good" if isinstance(delta, (int, float)) and delta <= -5
            else "warn" if isinstance(delta, (int, float)) and delta >= 5
            else "flat"
        ),
        "verdict": result.get("verdict", ""),
        "rows": rows,
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
