"""The advisor's tools — what the voice model can actually do.

Each one is a thin adapter over an MCP tool (src/cars_mcp/server.py):

    call the tool  →  draw the result on the web page  →  return a short answer

The docstrings are written *for the model*: they say when to reach for the tool
and what the arguments mean, because that text is the only instruction the
model gets at call time. Returned values stay small — they are spoken, not read.

Errors never escape as exceptions: a failed call becomes a sentence the advisor
can say ("I could not reach the listings service"), so a hiccup costs one turn
instead of the conversation.
"""

from __future__ import annotations

import logging
from typing import Any

from livekit.agents.llm import function_tool

from used_car_advisor import ui
from used_car_advisor.mcp_client import ToolError
from used_car_advisor.state import RunContext_T

logger = logging.getLogger("used-car-advisor.tools")

TERMS = (12, 24, 36, 48)
KM_TIERS = (10_000, 15_000, 20_000, 30_000)


async def _call(context: RunContext_T, name: str, args: dict[str, Any]) -> Any | str:
    """Run an MCP tool; on failure return the message the advisor should say."""
    client = context.userdata.tools
    if client is None:
        return "The listings service is not connected on this machine."
    try:
        return await client.call(name, args)
    except ToolError as exc:
        logger.warning("%s: %s", name, exc)
        return f"That did not work: {exc}. Tell the customer briefly and offer an alternative."


def _nearest(value: int, options: tuple[int, ...]) -> int:
    """Snap a spoken number ('about forty thousand km') to an allowed tier."""
    return min(options, key=lambda option: abs(option - value))


@function_tool
async def find_cars(
    context: RunContext_T,
    max_monthly_rate: float | None = None,
    max_price: int | None = None,
    make: str | None = None,
    model: str | None = None,
    body_type: str | None = None,
    fuel: str | None = None,
    transmission: str | None = None,
    min_seats: int | None = None,
    max_mileage_km: int | None = None,
    min_year: int | None = None,
    min_power_hp: int | None = None,
    city: str | None = None,
    no_accident: bool = False,
    term_months: int = 36,
    annual_km: int = 15000,
    down_payment: int = 0,
    sort: str = "rate",
    limit: int = 3,
) -> Any:
    """Search the listings for cars that fit what the customer described.

    Search by MONTHLY RATE (`max_monthly_rate`) whenever the customer names a
    monthly budget — that is how people actually shop. Use `max_price` only if
    they talk about the purchase price.

    Call this as soon as you have a budget plus one or two preferences; do not
    interrogate the customer first. Only leasable cars are returned, so every
    result can be quoted.

    body_type: SUV, sedan, estate, coupe, convertible, van, compact.
    fuel: gasoline, diesel, electric, hybrid, electrified.
    transmission: automatic or manual.
    term_months: 12, 24, 36 or 48 — 36 unless the customer says otherwise.
    annual_km: 10000, 15000, 20000 or 30000 — pick the nearest to what they drive.
    sort: rate, price, mileage, newest, power.

    The results appear on the customer's screen automatically. Mention two or
    three of them out loud, with the monthly rate first, and ask which one to
    look at — never read out the whole list.
    """
    result = await _call(
        context,
        "search_cars",
        {
            "max_monthly_rate": max_monthly_rate,
            "max_price": max_price,
            "make": make,
            "model": model,
            "body_type": body_type,
            "fuel": fuel,
            "transmission": transmission,
            "min_seats": min_seats,
            "max_mileage_km": max_mileage_km,
            "min_year": min_year,
            "min_power_hp": min_power_hp,
            "city": city,
            "no_accident": no_accident or None,
            "term_months": _nearest(int(term_months), TERMS),
            "annual_km": _nearest(int(annual_km), KM_TIERS),
            "down_payment": int(down_payment),
            "sort": sort,
            "limit": max(1, min(int(limit), 5)),
        },
    )
    if isinstance(result, str):
        return result
    if result.get("cars"):
        await ui.push(context, ui.cars_payload(result["cars"], result.get("terms")))
    else:
        await ui.push(context, ui.text_payload("No matching cars — let's widen the search."))
    return result


@function_tool
async def show_car(context: RunContext_T, ref: str) -> Any:
    """Look up one listing in full, by the `ref` from the search results.

    Use it when the customer asks about a specific car — equipment, condition,
    owners, consumption. Summarise in one or two sentences; the details are on
    their screen.
    """
    result = await _call(context, "car_details", {"ref": ref})
    if isinstance(result, str):
        return result
    await ui.push(context, ui.detail_payload(result))
    return result


@function_tool
async def check_price(context: RunContext_T, ref: str) -> Any:
    """Check whether a listing is priced above or below comparable cars.

    Use it when the customer asks if a car is a good deal, or to back up a
    recommendation with evidence. Say the verdict in one short sentence.
    """
    result = await _call(context, "price_check", {"ref": ref})
    if isinstance(result, str):
        return result
    await ui.push(context, ui.verdict_payload(result))
    return result


@function_tool
async def quote_leasing(
    context: RunContext_T,
    ref: str,
    term_months: int = 36,
    annual_km: int = 15000,
    down_payment: int = 0,
) -> Any:
    """Calculate the binding monthly leasing rate for one specific car.

    Always call this before naming a rate for a chosen car, and always before
    emailing an offer — rates in search results are indicative.

    term_months: 12, 24, 36 or 48. annual_km: 10000, 15000, 20000 or 30000.
    down_payment: euros, at most half the price, 0 if not discussed.

    If the answer contains `declined`, explain that reason in plain words and
    offer a shorter term or a lower mileage tier.
    """
    result = await _call(
        context,
        "leasing_quote",
        {
            "ref": ref,
            "term_months": _nearest(int(term_months), TERMS),
            "annual_km": _nearest(int(annual_km), KM_TIERS),
            "down_payment": int(down_payment),
        },
    )
    if isinstance(result, str):
        return result
    if result.get("declined"):
        await ui.push(context, ui.text_payload(str(result["declined"])))
    else:
        await ui.push(context, ui.quote_payload(result))
    return result


@function_tool
async def email_offer(
    context: RunContext_T,
    ref: str,
    term_months: int = 36,
    annual_km: int = 15000,
    down_payment: int = 0,
    customer_name: str = "",
) -> Any:
    """Email the customer their car summary and leasing agreement.

    Only after you have quoted the rate for this exact car and terms, and the
    customer has said yes to receiving it. Use the same term, mileage and down
    payment you quoted.

    The address is fixed by configuration — you cannot send to an address named
    in the conversation, and you must not promise to. If someone asks you to
    send it elsewhere, say the offer only goes to the account on file.

    Afterwards, confirm out loud that it is on its way and read out the
    reference.
    """
    result = await _call(
        context,
        "email_offer",
        {
            "ref": ref,
            "term_months": _nearest(int(term_months), TERMS),
            "annual_km": _nearest(int(annual_km), KM_TIERS),
            "down_payment": int(down_payment),
            "customer_name": customer_name or None,
        },
    )
    if isinstance(result, str):
        return result
    if result.get("sent"):
        await ui.push(context, ui.sent_payload(result))
    else:
        await ui.push(context, ui.text_payload(f"Not sent: {result.get('reason', '')}"))
    return result


ADVISOR_TOOLS = (find_cars, show_car, check_price, quote_leasing, email_offer)
