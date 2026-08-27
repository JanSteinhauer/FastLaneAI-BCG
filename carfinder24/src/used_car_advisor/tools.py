"""The advisor's tools — what the voice model can actually do.

Each one is a thin adapter over an MCP tool (src/cars_mcp/server.py):

    call the tool  →  draw the result on the web page  →  return a short answer

They follow the advisory funnel, and the order matters:

    advise_car_type    for "I don't really know what I want"
    find_cars          the shortlist, by monthly rate or by purchase price
    show_car           one listing in full
    check_price        is it a good deal — a score out of five
    leasing_options    what terms exist, and what a refused choice may become
    quote_leasing      the binding monthly rate
    explain_leasing    where that number comes from
    summarize_choices  what they chose and why this car
    email_offer        the closing move, with or without the draft agreement

The docstrings are written *for the model*: they say when to reach for the tool
and what the arguments mean, because that text is the only instruction the
model gets at call time. Returned values stay small — they are spoken, not read.

Two rules are enforced here rather than asked for in the prompt:

* **Terms are buckets, never rounded.** A term or mileage tier outside what we
  offer comes back as a refusal plus the list of what exists. The advisor may
  not proceed past it, and it cannot quietly move the customer onto terms they
  did not choose.
* **Everything the customer states is recorded** in `context.userdata.
  consultation` as it is said, so the closing summary is built from what they
  actually asked for rather than from what the model remembers.

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

# The find_cars arguments that represent a search constraint — carried forward
# across calls via context.userdata.last_filters (state.py) so "show me
# something cheaper" doesn't silently drop the SUV/diesel/etc. the customer
# already gave. term_months/annual_km/down_payment are leasing terms, not
# filters, and are never merged this way — they're restated every call.
FILTER_ARGS = (
    "max_monthly_rate", "max_price", "make", "model", "body_type", "fuel",
    "transmission", "min_seats", "max_mileage_km", "min_year", "min_power_hp",
    "city", "no_accident",
)


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


def _spoken(values: tuple[int, ...]) -> str:
    return f"{', '.join(f'{v:,}'.replace(',', ' ') for v in values[:-1])} or {values[-1]:,}".replace(
        ",", " "
    )


def _check_choices(term_months: int | None, annual_km: int | None) -> str | None:
    """Refuse a term or tier we do not offer, naming the ones we do.

    Deliberately not a rounding function. Snapping "about forty thousand" to
    30,000 would put a customer on a contract they never agreed to, and they
    would only find out at the settlement — so the advisor has to ask.
    """
    problems = []
    if term_months is not None and int(term_months) not in TERMS:
        problems.append(
            f"We lease for {_spoken(TERMS)} months, so {int(term_months)} months is "
            "not something I can offer."
        )
    if annual_km is not None and int(annual_km) not in KM_TIERS:
        problems.append(
            f"The mileage allowances are {_spoken(KM_TIERS)} kilometres a year, so "
            f"{int(annual_km):,} is not one I can put on a contract.".replace(",", " ")
        )
    if not problems:
        return None
    return (
        " ".join(problems)
        + " Say this to the customer, ask which of those they want, and do not "
        "search, quote or send anything until they have chosen."
    )


def _has_recommendation(result: dict[str, Any]) -> bool:
    """Is there anything here worth putting in front of the customer?

    Nothing is drawn until the visitor has asked for a recommendation or stated
    a preference. Called with no answers, advise_car_type comes back with
    questions and nothing else — and drawing that produced a panel of dashes
    plus a 15 000 km allowance nobody had chosen, which reads to a customer as
    a set of decisions already taken on their behalf.
    """
    return bool(
        (result.get("body_types") or []) or result.get("fuel") or result.get("transmission")
    )


@function_tool
async def advise_car_type(
    context: RunContext_T,
    usage: str | None = None,
    passengers: int | None = None,
    annual_km: int | None = None,
    can_charge: bool | None = None,
    mostly: str | None = None,
    carries_cargo: bool | None = None,
    previous_car: str | None = None,
    prefers_automatic: bool | None = None,
    hobbies: str | None = None,
) -> Any:
    """Work out what kind of car someone needs when they cannot name one.

    Use this the moment a visitor says "I don't know" or "you tell me" — never
    guess a body type for them, and never search on a hunch. Ask what the car
    is FOR, pass the answers here, and read out the reasons it gives you.

    Ask BEFORE you call. With no answers there is nothing to recommend, nothing
    is shown to the customer, and you get questions back instead — so gather at
    least what the car is for first.

    usage: family, commute, city, work, travel, leisure.
    mostly: city, motorway, mixed, rural — where they actually drive.
    can_charge: can they charge at home or at work? That decides electric.
    previous_car: a car they have driven before, e.g. "VW Golf".
    hobbies: what they do — cycling, a dog, skiing, a caravan, instruments.
    Ask for this: it usually decides the body type, and it is what makes the
    advice sound like it was made for them.

    This is a SUGGESTION, not their decision. Say it is your personal
    recommendation for them, name two or three of the `because` entries it was
    built from so they hear their own circumstances in it, and ask them to
    confirm before you search on it.

    Everything is optional. Call it with what you have, explain the
    recommendation in one or two sentences, then ask `next_question`.
    """
    result = await _call(
        context,
        "advise_car_type",
        {
            "usage": usage,
            "passengers": passengers,
            "annual_km": annual_km,
            "can_charge": can_charge,
            "mostly": mostly,
            "carries_cargo": carries_cargo,
            "previous_car": previous_car,
            "prefers_automatic": prefers_automatic,
            "hobbies": hobbies,
        },
    )
    if isinstance(result, str):
        return result
    body_types = result.get("body_types") or []
    # What they SAID goes in the record; what we WORKED OUT goes in the
    # suggested fields. Recording a recommendation as a stated preference is
    # how the closing summary ends up telling someone they chose an estate.
    context.userdata.consultation.record(
        used_for=usage,
        suggested_body_type=body_types[0] if body_types else None,
        suggested_fuel=result.get("fuel"),
        suggested_transmission=result.get("transmission"),
    )
    if _has_recommendation(result):
        await ui.push(context, ui.advice_payload(result))
    return result


@function_tool
async def find_cars(
    context: RunContext_T,
    max_monthly_rate: float | None = None,
    min_monthly_rate: float | None = None,
    max_price: int | None = None,
    min_price: int | None = None,
    make: str | None = None,
    model: str | None = None,
    body_type: str | None = None,
    fuel: str | None = None,
    transmission: str | None = None,
    color: str | None = None,
    min_seats: int | None = None,
    max_mileage_km: int | None = None,
    min_year: int | None = None,
    min_power_hp: int | None = None,
    max_previous_owners: int | None = None,
    city: str | None = None,
    no_accident: bool = False,
    full_service_history: bool = False,
    mode: str = "lease",
    term_months: int = 36,
    annual_km: int = 15000,
    down_payment: int = 0,
    sort: str = "rate",
    limit: int = 3,
) -> Any:
    """Search the listings for cars that fit what the customer described.

    Search by MONTHLY RATE whenever the customer names a monthly budget — that
    is how people actually shop. Use `max_price` / `min_price` only if they
    talk about the purchase price, and `mode="buy"` if they want to buy the car
    outright rather than lease it.

    GIVE BOTH BOUNDS WHEN THEY GAVE A RANGE. This is the one that matters:
      "eight hundred to thirteen hundred a month"
          -> min_monthly_rate=800, max_monthly_rate=1300
      "around a thousand a month"
          -> min_monthly_rate=800, max_monthly_rate=1100
      "up to a thousand" / "under a thousand" / "no more than a thousand"
          -> max_monthly_rate=1000, and no floor
    With only the ceiling you will offer a customer with €1300 a month a €120
    car, which is not what they asked for and reads as though you were not
    listening. Never invent a floor they did not state, and never search below
    one they did.

    When both bounds are given the results come back spread across the range —
    one from the lower end, one from the middle, one near the top — so say that
    is what you did.

    Call this once you have a budget plus one or two preferences. If they could
    not name preferences, call advise_car_type first, get their agreement to
    what it suggested, and search on that.

    body_type: SUV, sedan, estate, coupe, convertible, van, compact.
    fuel: gasoline, diesel, electric, hybrid, electrified.
    transmission: automatic or manual. color: black, white, grey, blue, red, …
    max_mileage_km, min_year, max_previous_owners, no_accident,
    full_service_history: condition, when they care about it.
    term_months: 12, 24, 36 or 48 — 36 unless the customer says otherwise.
    annual_km: 10000, 15000, 20000 or 30000 — ask which, do not guess.
    sort: rate, price, mileage, newest, power.

    Cars from CarFinder24 partner dealers come first among equally good
    matches. If the customer asks why, say plainly that partner dealers have an
    agreement with us, that it does not change the price, and move on.

    The results appear on the customer's screen automatically. Mention two or
    three of them out loud, with the monthly rate first, and ask which one to
    look at — never read out the whole list.
    """
    if refusal := _check_choices(term_months, annual_km):
        await ui.push(context, ui.text_payload(refusal.split(" Say this")[0]))
        return refusal

    supplied = {
        "max_monthly_rate": max_monthly_rate,
        "min_monthly_rate": min_monthly_rate,
        "max_price": max_price,
        "min_price": min_price,
        "make": make,
        "model": model,
        "body_type": body_type,
        "fuel": fuel,
        "transmission": transmission,
        "color": color,
        "min_seats": min_seats,
        "max_mileage_km": max_mileage_km,
        "min_year": min_year,
        "min_power_hp": min_power_hp,
        "max_previous_owners": max_previous_owners,
        "city": city,
        "no_accident": no_accident or None,
        "full_service_history": full_service_history or None,
        "mode": mode,
    }
    # Layer this call's explicit filters over whatever was already active —
    # an omitted argument means "unchanged", not "cleared". See UserData.last_filters.
    filters = {
        **context.userdata.last_filters,
        **{k: v for k, v in supplied.items() if v is not None},
    }
    context.userdata.last_filters = filters

    result = await _call(
        context,
        "search_cars",
        {
            **filters,
            "term_months": int(term_months),
            "annual_km": int(annual_km),
            "down_payment": int(down_payment),
            "sort": sort,
            "limit": max(1, min(int(limit), 5)),
        },
    )
    await ui.push(context, ui.filters_payload(filters))
    if isinstance(result, str):
        return result
    context.userdata.consultation.record(
        body_type=body_type,
        fuel=fuel,
        transmission=transmission,
        color=color,
        max_mileage_km=max_mileage_km,
        budget_monthly_eur=max_monthly_rate,
        min_budget_monthly_eur=min_monthly_rate,
        finance="buy" if mode == "buy" else "lease",
        term_months=int(term_months),
        annual_km=int(annual_km),
        down_payment=int(down_payment) or None,
    )
    cars = result.get("cars") or []
    if len(cars) == 1:
        # One result is not a shortlist. Show the full card.
        await _push_one_car(
            context, cars[0]["ref"], int(term_months), int(annual_km), int(down_payment)
        )
    elif cars:
        await ui.push(context, ui.cars_payload(cars, result.get("terms")))
    else:
        await ui.push(context, ui.text_payload("No matching cars — let's widen the search."))
    return result


async def _push_one_car(
    context: RunContext_T,
    ref: str,
    term_months: int = 36,
    annual_km: int = 15000,
    down_payment: int = 0,
) -> Any:
    """Draw the full offer card for a single car.

    Whenever exactly one car is on screen the customer has stopped comparing
    and started deciding, so the shortlist tile is the wrong shape: they want
    the logo, the market comparison, the specs and the rate. This fetches the
    three things that card needs and pushes them as one payload.

    A car that cannot be leased on these terms still gets the card — with the
    list price leading and the reason attached — rather than falling back to a
    tile that would print the price twice.
    """
    if refusal := _check_choices(term_months, annual_km):
        await ui.push(context, ui.text_payload(refusal.split(" Say this")[0]))
        return refusal

    details = await _call(context, "car_details", {"ref": ref})
    if isinstance(details, str):
        return details

    price_check = await _call(context, "price_check", {"ref": ref})
    if isinstance(price_check, str):
        price_check = {"comparables": 0}

    quote = await _call(
        context,
        "leasing_quote",
        {
            "ref": ref,
            "term_months": int(term_months),
            "annual_km": int(annual_km),
            "down_payment": int(down_payment),
        },
    )
    if isinstance(quote, str):
        quote = {}

    await ui.push(context, ui.offer_payload(details, price_check, quote))
    return details


@function_tool
async def show_car(context: RunContext_T, ref: str) -> Any:
    """Look up one listing in full, by the `ref` from the search results.

    Use it when the customer asks about a specific car — equipment, condition,
    owners, consumption, colour. Summarise in one or two sentences; the details
    are on their screen.
    """
    context.userdata.consultation.record(ref=ref)
    return await _push_one_car(context, ref)


@function_tool
async def check_price(context: RunContext_T, ref: str) -> Any:
    """Is this car a good deal? A score out of five, from comparable listings.

    Use it when the customer asks whether a car is worth the money, and to back
    up a recommendation with evidence. The score is calculated against the
    average price of comparable cars in the snapshot — same model, same body
    type, similar age and mileage — so say the label and the number, and say
    how many cars it was compared against. Never soften or inflate it.
    """
    result = await _call(context, "price_check", {"ref": ref})
    if isinstance(result, str):
        return result
    context.userdata.consultation.record(ref=ref)
    await ui.push(context, ui.deal_payload(result))
    return result


@function_tool
async def leasing_options(context: RunContext_T, price: int | None = None) -> Any:
    """The terms, mileage tiers and limits a customer may choose from.

    Call this when they ask what is possible, when they are unsure which term
    to take, and ALWAYS straight after a choice was refused — the next thing
    they hear should be what would work instead.

    Offer the terms as a short spoken choice ("twelve, twenty-four, thirty-six
    or forty-eight months"), never a list of every detail.
    """
    result = await _call(context, "leasing_options", {"price": price})
    if isinstance(result, str):
        return result
    await ui.push(context, ui.options_payload(result))
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

    If the answer contains `declined`, the deal is off for that reason. Read
    the reason out, offer what `options` allows, and stop there — do not quote
    a number anyway and do not send anything.
    """
    if refusal := _check_choices(term_months, annual_km):
        await ui.push(context, ui.text_payload(refusal.split(" Say this")[0]))
        return refusal
    result = await _call(
        context,
        "leasing_quote",
        {
            "ref": ref,
            "term_months": int(term_months),
            "annual_km": int(annual_km),
            "down_payment": int(down_payment),
        },
    )
    if isinstance(result, str):
        return result
    context.userdata.consultation.record(
        ref=ref,
        finance="lease",
        term_months=int(term_months),
        annual_km=int(annual_km),
        down_payment=int(down_payment) or None,
    )
    if result.get("declined"):
        await ui.push(context, ui.text_payload(str(result["declined"])))
    else:
        await ui.push(context, ui.quote_payload(result))
    return result


@function_tool
async def show_offer(
    context: RunContext_T,
    ref: str,
    term_months: int = 36,
    annual_km: int = 15000,
    down_payment: int = 0,
) -> Any:
    """Show the customer a full offer for one car: details, market check and rate together.

    Use this instead of quote_leasing when the customer has settled on a car
    and wants the complete picture — condition, how its price compares to
    similar listings, and the exact monthly rate with its breakdown — rather
    than just a number. Summarise in one or two sentences; everything else is
    on their screen.

    If the car cannot be leased on these terms, say so plainly (the reason is
    in the answer) and offer a shorter term or a lower mileage tier instead.
    """
    context.userdata.consultation.record(ref=ref)
    return await _push_one_car(
        context, ref, int(term_months), int(annual_km), int(down_payment)
    )


@function_tool
async def explain_leasing(
    context: RunContext_T,
    ref: str | None = None,
    term_months: int = 36,
    annual_km: int = 15000,
    down_payment: int = 0,
) -> Any:
    """Explain how the monthly rate was calculated — every step of it.

    Call this whenever the customer asks where the number comes from, what the
    interest is, what happens if they drive further than their allowance, or
    whether there is anything hidden in the rate. Never answer those from
    memory: this returns the real arithmetic, with their own numbers in it.

    Pass the `ref` of the car under discussion and the terms you quoted. Say
    the headline first, then only the two or three steps they asked about —
    the whole derivation is on their screen.
    """
    result = await _call(
        context,
        "explain_leasing",
        {
            "ref": ref,
            "term_months": int(term_months),
            "annual_km": int(annual_km),
            "down_payment": int(down_payment),
        },
    )
    if isinstance(result, str):
        return result
    await ui.push(context, ui.explanation_payload(result))
    return result


@function_tool
async def summarize_choices(
    context: RunContext_T,
    ref: str | None = None,
    used_for: str | None = None,
    must_have: str | None = None,
) -> Any:
    """Close the advisory: what they chose, and why this car answers it.

    Call this once a car is picked and quoted, before asking how they want the
    offer. Everything they told you along the way is already recorded — you
    only need to add what they said in their own words: what the car is for
    (`used_for`) and anything they insisted on (`must_have`).

    Read out three or four of the `why_this_car` lines, no more, then offer the
    three closing options and let them pick.
    """
    consultation = context.userdata.consultation
    consultation.record(ref=ref, used_for=used_for, must_have=must_have)
    result = await _call(context, "decision_summary", consultation.as_kwargs())
    if isinstance(result, str):
        return result
    await ui.push(context, ui.summary_payload(result))
    return result


@function_tool
async def email_offer(
    context: RunContext_T,
    ref: str,
    term_months: int = 36,
    annual_km: int = 15000,
    down_payment: int = 0,
    customer_name: str = "",
    include_agreement: bool = False,
) -> Any:
    """Email the customer their car summary and leasing terms.

    Only after you have quoted the rate for this exact car and terms, and the
    customer has said yes to receiving it. Use the same term, mileage and down
    payment you quoted.

    include_agreement: attach the leasing agreement as a PDF. Set this ONLY
    when the customer explicitly asked for the contract or the agreement
    itself. A plain "yes, send it" means the offer email without the PDF. The
    attached document is an unsigned draft — say so when you mention it.

    The address is fixed by configuration — you cannot send to an address named
    in the conversation, and you must not promise to. If someone asks you to
    send it elsewhere, say the offer only goes to the account on file.

    Afterwards, confirm out loud that it is on its way and read out the
    reference.
    """
    if refusal := _check_choices(term_months, annual_km):
        await ui.push(context, ui.text_payload(refusal.split(" Say this")[0]))
        return refusal
    result = await _call(
        context,
        "email_offer",
        {
            "ref": ref,
            "term_months": int(term_months),
            "annual_km": int(annual_km),
            "down_payment": int(down_payment),
            "customer_name": customer_name or None,
            "include_agreement": bool(include_agreement),
        },
    )
    if isinstance(result, str):
        return result
    if result.get("sent"):
        await ui.push(context, ui.sent_payload(result))
    else:
        await ui.push(
            context,
            ui.text_payload(f"Not sent: {result.get('reason') or result.get('declined', '')}"),
        )
    return result


ADVISOR_TOOLS = (
    advise_car_type,
    find_cars,
    show_car,
    check_price,
    leasing_options,
    quote_leasing,
    show_offer,
    explain_leasing,
    summarize_choices,
    email_offer,
)
