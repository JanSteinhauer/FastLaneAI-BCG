"""What the visitor sees while the agent talks.

A voice agent that only talks makes the listener hold six numbers in their head.
Every tool that produces something concrete — a shortlist, a spec, a rate, a
sent email — also pushes a card to the web page over the LiveKit data channel
(topic "ui"), so the customer can *see* the shortlist while hearing the advice.

Payload shapes understood by frontend/src/main.jsx:

    {"type": "cars",    "cars": [...]}    listing cards
    {"type": "quote",   ...}              the leasing agreement card
    {"type": "sent",    ...}              email confirmation
    {"type": "text",    "text": "..."}    a plain bubble
    {"type": "offer",   ...}              car + price-check + leasing, fused (show_offer)
    {"type": "filters", "active": {...}}  the filters find_cars is currently applying

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


# Customer word (as find_cars receives it) -> the filter panel's icon key.
# Mirrors the vocabulary in cars_mcp.server.BODY_TYPES; kept as a small local
# copy rather than an import because the tool server and the agent worker are
# separate processes (see docs/ARCHITECTURE.md) — this mapping is presentation
# only, nothing here reaches SQL.
_BODY_TYPE_ICON = {
    "suv": "suv", "off-road": "suv", "pick-up": "suv",
    "sedan": "sedan", "saloon": "sedan",
    "estate": "wagon", "station wagon": "wagon", "wagon": "wagon",
    "coupe": "coupe",
    "convertible": "convertible", "cabrio": "convertible",
    "van": "van",
    "compact": "compact", "small": "compact",
}

# The subset of find_cars' arguments that represent an actual search
# constraint (not a leasing term like term_months, and not paging like limit).
_FILTER_KEYS = (
    "max_monthly_rate", "max_price", "make", "model", "body_type", "fuel",
    "transmission", "min_seats", "max_mileage_km", "min_year", "min_power_hp",
    "city", "no_accident",
)


def filters_payload(active: dict[str, Any]) -> dict:
    """Every constraint find_cars is currently applying, for the filter panel.

    `active` is the *merged* filter set (this call's args layered over the
    session's last search — see UserData.last_filters), so a filter the
    customer mentioned two turns ago still shows as active here.
    """
    body_type = active.get("body_type")
    icon_key = _BODY_TYPE_ICON.get((body_type or "").strip().lower())
    return {
        "type": "filters",
        "active": {k: active[k] for k in _FILTER_KEYS if active.get(k) not in (None, False)},
        "body_type_icon": icon_key,
    }


def offer_payload(details: dict[str, Any], price_check: dict[str, Any], quote: dict[str, Any]) -> dict:
    """One car, fully priced — car_details + price_check + leasing_quote fused.

    For the moment the customer has picked a specific car: everything the
    OfferCard needs in one payload, so the frontend never has to reconcile
    three separate tool responses itself.
    """
    term_months = quote.get("term_months")
    annual_km = quote.get("annual_km")
    monthly_rate = quote.get("monthly_rate_eur")
    price = details.get("price_eur")
    total_cost = quote.get("total_cost_eur")
    years = (term_months / 12) if term_months else None
    cost_per_km = (
        total_cost / (annual_km * years)
        if total_cost and annual_km and years
        else None
    )
    leasing_factor_pct = (
        round(monthly_rate / price * 100, 2) if monthly_rate and price else None
    )

    comparison = None
    if (price_check.get("comparables") or 0) > 0 and price_check.get("median_price_eur") is not None:
        delta = price_check.get("difference_pct", 0)
        comparison = {
            "median_price_eur": price_check["median_price_eur"],
            "range_eur": price_check.get("range_eur"),
            "difference_pct": delta,
            "direction": "below" if delta <= -5 else "above" if delta >= 5 else "even",
            "comparables": price_check["comparables"],
        }

    return {
        "type": "offer",
        "ref": details.get("ref"),
        "make": details.get("make"),
        "title": details.get("title"),
        "body_type": details.get("body_type"),
        "body_color": details.get("body_color"),
        "year": details.get("year"),
        "mileage_km": details.get("mileage_km"),
        "power_hp": details.get("power_hp"),
        "fuel": details.get("fuel"),
        "transmission": details.get("transmission"),
        "drive_train": details.get("drive_train"),
        "seller": details.get("seller"),
        "city": details.get("city"),
        "ratings_average": details.get("ratings_average"),
        "ratings_count": details.get("ratings_count"),
        "had_accident": details.get("had_accident"),
        "full_service_history": details.get("full_service_history"),
        "previous_owners": details.get("previous_owners"),
        "consumption_l_100km": details.get("consumption_l_100km"),
        "co2_g_km": details.get("co2_g_km"),
        "price_eur": price,
        "monthly_rate_eur": monthly_rate,
        "leasing_factor_pct": leasing_factor_pct,
        "term_months": term_months,
        "annual_km": annual_km,
        "down_payment_eur": quote.get("down_payment_eur"),
        "breakdown": quote.get("breakdown", {}),
        "total_cost_eur": total_cost,
        "cost_per_km_eur": round(cost_per_km, 2) if cost_per_km is not None else None,
        "comparison": comparison,
        "footnote": "Indicative offer · incl. VAT · not a credit agreement · final terms confirmed by the dealer.",
    }
