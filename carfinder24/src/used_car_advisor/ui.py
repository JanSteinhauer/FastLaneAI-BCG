"""What the visitor sees while the agent talks.

A voice agent that only talks makes the listener hold six numbers in their head.
Every tool that produces something concrete — a shortlist, a spec, a rate, a
sent email — also pushes a card to the web page over the LiveKit data channel
(topic "ui"), so the customer can *see* the shortlist while hearing the advice.

Payload shapes understood by frontend/src/main.jsx:

    {"type": "cars",  "cars": [...]}    listing cards
    {"type": "quote", ...}              the leasing agreement card
    {"type": "sent",  ...}              email confirmation
    {"type": "text",  "text": "..."}    a plain bubble

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
