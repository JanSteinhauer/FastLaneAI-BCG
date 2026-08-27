"""From "I don't really know what I want" to a search filter.

Most visitors cannot name a body type, and the ones who can often name the
wrong one. The funnel in `docs/ARCHITECTURE.md` therefore has a second path:
ask what the car is *for*, and derive the shape of the car from the answers.

That derivation lives here rather than in the prompt, for the same reason the
leasing rate does: it has to be the same every time, it has to be explainable
("an estate, because two child seats and a dog"), and it must not quietly
change when someone rewrites a paragraph of instructions.

Everything is optional. The advisor calls this with whatever it has, gets back
a profile plus the one question most worth asking next, and asks that.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cars_leasing.model import KM_TIERS, TERMS


def _km(value: int) -> str:
    """15000 -> '15 000'; a comma in a spoken number is read as a pause."""
    return f"{value:,}".replace(",", " ")

# -- the vocabulary the advisor may pass in ----------------------------------
# Deliberately the words people actually say. Anything else is ignored rather
# than rejected: a half-understood answer should still narrow the search.
USES = {
    "family": "carrying a family",
    "commute": "commuting",
    "city": "city driving",
    "work": "work and transporting things",
    "travel": "long trips and holidays",
    "leisure": "occasional and leisure driving",
}
ROADS = {"city", "motorway", "mixed", "rural"}

DEFAULT_TERM = 36


@dataclass
class Profile:
    """What kind of car this person needs, and why."""

    body_types: list[str] = field(default_factory=list)  # search vocabulary
    fuel: str | None = None
    transmission: str | None = None
    min_seats: int | None = None
    annual_km: int = 15_000
    term_months: int = DEFAULT_TERM
    reasons: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "body_types": self.body_types,
            "fuel": self.fuel,
            "transmission": self.transmission,
            "min_seats": self.min_seats,
            "annual_km": self.annual_km,
            "term_months": self.term_months,
            "reasons": self.reasons,
            "next_question": self.open_questions[0] if self.open_questions else None,
            "open_questions": self.open_questions,
            "search_hint": (
                "Search with body_type = the first entry of body_types, plus the "
                "fuel and transmission above. Offer the alternatives only if the "
                "first search comes back thin."
            ),
        }


def recommend_profile(
    *,
    usage: str | None = None,
    passengers: int | None = None,
    annual_km: int | None = None,
    can_charge: bool | None = None,
    mostly: str | None = None,
    carries_cargo: bool | None = None,
    previous_car_body_type: str | None = None,
    prefers_automatic: bool | None = None,
) -> Profile:
    """Turn use-case answers into a car profile, with a reason for every choice.

    `previous_car_body_type` is the body type of a car they have driven before
    (looked up in the listings, not guessed) — people are happiest in roughly
    the size they are used to, so it breaks ties.
    """
    profile = Profile()
    use = (usage or "").strip().lower()
    road = (mostly or "").strip().lower()
    if road not in ROADS:
        road = ""

    # -- size and shape ------------------------------------------------------
    if passengers is not None and passengers >= 6:
        profile.body_types = ["van", "estate"]
        profile.min_seats = 7
        profile.reasons.append(
            f"{passengers} people only fit in a van or a large estate, so that is "
            "where I would start."
        )
    elif use == "family" or (passengers is not None and passengers >= 4):
        profile.body_types = ["estate", "SUV", "van"]
        profile.min_seats = 5
        profile.reasons.append(
            "For a family the boot matters more than the badge — an estate gives "
            "you the most space per euro, an SUV the easier loading height."
        )
    elif use == "city":
        profile.body_types = ["compact", "sedan"]
        profile.reasons.append(
            "In the city a compact car is easier to park and cheaper to run; "
            "anything larger you pay for twice."
        )
    elif use == "work":
        profile.body_types = ["van", "estate", "SUV"]
        profile.reasons.append(
            "If the car has to earn its keep, load space is the deciding feature."
        )
    elif use == "travel":
        profile.body_types = ["estate", "sedan", "SUV"]
        profile.reasons.append(
            "For long trips, comfort on the motorway matters most — an estate or "
            "a sedan is quieter and steadier than something tall."
        )
    elif use in {"commute", "leisure"}:
        profile.body_types = ["compact", "sedan", "estate"]
        profile.reasons.append(
            "For that kind of driving a compact or a sedan is the sensible "
            "middle: cheap to run, comfortable enough for a long day."
        )
    else:
        profile.open_questions.append(
            "What will you mainly use the car for — family, commuting, work, or "
            "longer trips?"
        )

    if carries_cargo and "estate" not in profile.body_types:
        profile.body_types.insert(0, "estate")
        profile.reasons.append("You mentioned carrying things, so an estate first.")

    if previous_car_body_type:
        previous = previous_car_body_type.strip().lower()
        if previous in {b.lower() for b in profile.body_types}:
            profile.reasons.append(
                "That is also roughly the size of what you have driven before, so "
                "it should feel familiar from the first drive."
            )
        elif previous:
            profile.body_types.append(previous_car_body_type)
            profile.reasons.append(
                f"You have driven a {previous_car_body_type} before — worth keeping "
                "on the list, since you already know the size works for you."
            )

    # -- fuel ----------------------------------------------------------------
    km = annual_km if annual_km is not None else None
    if can_charge is None:
        profile.open_questions.append(
            "Could you charge a car at home or at work? That decides whether "
            "electric is worth looking at."
        )
    if can_charge and (km is None or km <= 20_000) and road != "motorway":
        profile.fuel = "electric"
        profile.reasons.append(
            "You can charge and you are not doing motorway distances, which is "
            "exactly where electric is cheapest to run."
        )
    elif can_charge is False and road == "city":
        profile.fuel = "hybrid"
        profile.reasons.append(
            "Without a charger at home, a hybrid gives you the city fuel saving "
            "without ever needing a cable."
        )
    elif km is not None and km >= 20_000 and road in {"motorway", "mixed", ""}:
        profile.fuel = "diesel"
        profile.reasons.append(
            f"At {_km(km)} km a year a diesel still pays for itself on the motorway."
        )
    elif km is not None:
        profile.fuel = "gasoline"
        profile.reasons.append(
            "At that mileage a petrol car is the cheapest way in — you would not "
            "drive enough to earn back a diesel or an electric."
        )
    else:
        profile.open_questions.append("Roughly how many kilometres do you drive a year?")

    # -- transmission --------------------------------------------------------
    if prefers_automatic is True:
        profile.transmission = "automatic"
        profile.reasons.append("Automatic, as you asked.")
    elif prefers_automatic is False:
        profile.transmission = "manual"
        profile.reasons.append("Manual, as you asked.")
    elif profile.fuel == "electric":
        profile.reasons.append("Electric cars are automatic by nature, so that is settled.")
    elif use in {"city", "family"} or road == "city":
        profile.transmission = "automatic"
        profile.reasons.append(
            "In stop-and-go traffic an automatic is worth the small extra on the rate."
        )

    # -- how far, how long ---------------------------------------------------
    if km is not None:
        profile.annual_km = nearest_tier(km)
        if profile.annual_km != km:
            profile.reasons.append(
                f"Mileage allowances come in fixed steps, so "
                f"{_km(profile.annual_km)} km a year is the tier that covers your "
                f"{_km(km)} km."
            )
    profile.term_months = DEFAULT_TERM
    profile.open_questions.append(
        "And what would you like to spend per month? That is what I search on."
    )
    return profile


def nearest_tier(annual_km: int) -> int:
    """The smallest allowance that covers this mileage (the largest if none does).

    Note the asymmetry with `cars_leasing.model.validate_choices`: when the
    *customer* names a tier we refuse anything that is not one of ours, but
    when *we* recommend one we round up, never down — an allowance that is too
    small costs them at the end of the contract.
    """
    return next((tier for tier in KM_TIERS if tier >= annual_km), KM_TIERS[-1])


def term_advice(priority: str | None = None) -> dict[str, object]:
    """Which term to suggest, and the trade-off in one sentence each."""
    return {
        "terms_months": list(TERMS),
        "default": DEFAULT_TERM,
        "trade_off": {
            12: "Highest monthly rate, but you are free again in a year.",
            24: "A good fit if you expect your life to change — a job, a child, a move.",
            36: "The usual choice: the rate has come down a lot and the car is "
            "still young at the end.",
            48: "The lowest monthly rate. The car will be four years older when "
            "you hand it back, and you are committed for all of it.",
        },
        "suggested": (
            48 if (priority or "").lower() in {"cheapest", "lowest rate", "budget"}
            else 12 if (priority or "").lower() in {"flexible", "short"}
            else DEFAULT_TERM
        ),
    }
