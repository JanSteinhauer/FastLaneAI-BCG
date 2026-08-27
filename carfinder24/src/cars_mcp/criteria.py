"""What the conversation has established so far, as two fillable stages.

A voice call has no scrollback. Ten seconds after the customer says "twenty
thousand kilometres a year" there is nothing on screen confirming the advisor
heard it — so they repeat themselves, or worse, they don't and find out at the
quote. This module turns the conversation into a visible checklist: **the car**,
then **the leasing**, each with its own slots.

The slot vocabulary lives here, next to the data, for the same reason the
body-type synonyms do: the MCP layer knows that `body_type='estate'` means
"Station wagon" and that `annual_km` is what a customer calls *usage*. The agent
accumulates raw arguments and asks this layer to describe them; the browser just
draws what it is handed.

Nothing here asks the model to do extra work. Every value is lifted from
arguments it already passed, or results it already received — see
docs/PROGRESS_TRACKER.md.
"""

from __future__ import annotations

from typing import Any, Callable

Formatter = Callable[[Any], str]


def _plain(value: Any) -> str:
    return str(value)


def _eur(value: Any) -> str:
    return f"€{float(value):,.0f}".replace(",", " ")


def _eur_month(value: Any) -> str:
    return f"{_eur(value)} / month"


def _km(value: Any) -> str:
    return f"{int(value):,} km".replace(",", " ")


def _km_year(value: Any) -> str:
    return f"{int(value):,} km / year".replace(",", " ")


def _months(value: Any) -> str:
    return f"{int(value)} months"


def _hp(value: Any) -> str:
    return f"{int(value)} hp"


def _year(value: Any) -> str:
    return f"from {int(value)}"


def _pct(value: Any) -> str:
    return f"{float(value):.2f} %"


def _yes(value: Any) -> str:
    return "accident-free" if value else ""


# key -> (stage, label, formatter). Order is the order slots appear on screen:
# roughly the order a customer volunteers them.
SLOTS: dict[str, tuple[str, str, Formatter]] = {
    # --- the car ---------------------------------------------------------
    "body_type": ("car", "Type", _plain),
    "make": ("car", "Make", _plain),
    "model": ("car", "Model", _plain),
    "fuel": ("car", "Fuel", _plain),
    "transmission": ("car", "Gearbox", _plain),
    "min_seats": ("car", "Seats", _plain),
    "colour": ("car", "Colour", _plain),
    "min_power_hp": ("car", "Power", _hp),
    "max_mileage_km": ("car", "Mileage", _km),
    "min_year": ("car", "Age", _year),
    "electric_range_km": ("car", "Range", _km),
    "city": ("car", "Where", _plain),
    "no_accident": ("car", "Condition", _yes),
    # --- the leasing -----------------------------------------------------
    "max_monthly_rate": ("leasing", "Budget", _eur_month),
    "max_price": ("leasing", "Price cap", _eur),
    "annual_km": ("leasing", "Usage", _km_year),
    "term_months": ("leasing", "Term", _months),
    "down_payment": ("leasing", "Down payment", _eur),
    "monthly_rate_eur": ("leasing", "Monthly rate", _eur_month),
    "apr_pct": ("leasing", "Finance", _pct),
    "residual_value_eur": ("leasing", "Residual", _eur),
    "total_cost_eur": ("leasing", "Total", _eur),
}

STAGES: tuple[tuple[str, str], ...] = (("car", "The car"), ("leasing", "The leasing"))

# Slots that only ever arrive as a *result* — they are not things the customer
# asks for, so an empty one is not a gap in the conversation and must not drag
# the progress bar down before it is even possible to have them.
DERIVED = frozenset(
    {"monthly_rate_eur", "apr_pct", "residual_value_eur", "total_cost_eur",
     "electric_range_km", "colour"}
)


def describe(criteria: dict[str, Any]) -> dict[str, Any]:
    """Render accumulated criteria as two stages of filled and empty slots."""
    stages = []
    for key, title in STAGES:
        slots = []
        for slot, (stage, label, fmt) in SLOTS.items():
            if stage != key:
                continue
            value = criteria.get(slot)
            text = ""
            if value is not None and value != "" and value is not False:
                try:
                    text = fmt(value)
                except (TypeError, ValueError):
                    text = str(value)
            if not text and slot in DERIVED:
                continue  # results we cannot have yet: don't show an empty chip
            slots.append({"label": label, "value": text, "filled": bool(text)})
        filled = sum(1 for s in slots if s["filled"])
        stages.append(
            {
                "key": key,
                "title": title,
                "slots": slots,
                "filled": filled,
                "total": len(slots),
            }
        )
    return {
        "stages": stages,
        "car": criteria.get("car_title") or "",
        # Which stage the conversation is standing in. Not "any leasing slot is
        # filled" — customers open with a monthly budget, so that would light up
        # the leasing stage while they are still picking a car. Focus moves once
        # a specific car is on the table.
        "active": "leasing" if criteria.get("car_title") else "car",
    }
