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


@dataclass(frozen=True)
class Hobby:
    """What a pastime implies about the car, and how to say that out loud.

    A recommendation is only persuasive if the person can hear themselves in
    it, so what someone does at the weekend is a real input: it is usually the
    thing that decides between an estate and a sedan.
    """

    label: str  # for the "because you told me" line: "you cycle"
    body_types: tuple[str, ...]  # nudged up the list, never past a seat count
    reason: str


#: Matched by substring against whatever the visitor said, so "I cycle and we
#: have a dog" finds both. An unrecognised pastime is ignored rather than
#: rejected — the same rule the rest of this module follows for half-understood
#: answers. Keys are lowercase fragments; German words are included because
#: visitors say them even mid-English-sentence.
HOBBIES: tuple[tuple[tuple[str, ...], Hobby], ...] = (
    (
        ("cycl", "bike", "bicycle", "rad", "mountainbik"),
        Hobby(
            "you cycle",
            ("estate", "SUV"),
            "Bikes go inside an estate with the seats down — no rack, no roof "
            "bars, nothing to lift over your head.",
        ),
    ),
    (
        ("dog", "hund", "pet"),
        Hobby(
            "you have a dog",
            ("estate",),
            "A dog travels best on a flat boot floor, which is exactly what an "
            "estate gives you.",
        ),
    ),
    (
        ("ski", "snowboard", "winter sport"),
        Hobby(
            "you ski",
            ("SUV", "estate"),
            "For ski trips the load height and four-wheel drive are worth "
            "paying for, so I would look at an SUV or a big estate.",
        ),
    ),
    (
        ("golf bag", "golfing", "plays golf", "play golf"),
        Hobby(
            "you play golf",
            ("sedan", "estate"),
            "A golf bag needs boot depth rather than boot height, so a sedan "
            "or an estate carries it better than something tall.",
        ),
    ),
    (
        ("camp", "caravan", "trailer", "tow", "anhänger", "wohnwagen"),
        Hobby(
            "you tow a caravan or trailer",
            ("SUV", "estate"),
            "Towing needs weight behind it and a tow bar, which rules out the "
            "small end and points at an SUV or a large estate.",
        ),
    ),
    (
        ("surf", "kayak", "climb", "kletter", "diving", "tauch"),
        Hobby(
            "you carry bulky kit",
            ("estate", "SUV", "van"),
            "Kit that long only fits flat, so you want a load bay rather than "
            "a boot.",
        ),
    ),
    (
        ("music", "band", "dj", "drum", "cello", "guitar"),
        Hobby(
            "you carry instruments",
            ("estate", "van"),
            "Instruments want a square, flat space you can load without "
            "tilting anything.",
        ),
    ),
    (
        ("horse", "pferd", "reit"),
        Hobby(
            "you ride",
            ("SUV", "estate"),
            "A horsebox is a towing job, so the car needs the weight and the "
            "tow bar for it.",
        ),
    ),
)


def _hobbies(text: str | None) -> list[Hobby]:
    """Every pastime we recognise in what they said, in declaration order."""
    said = (text or "").strip().lower()
    if not said:
        return []
    return [hobby for keys, hobby in HOBBIES if any(key in said for key in keys)]


@dataclass
class Profile:
    """What kind of car this person needs, and why.

    `annual_km` stays None until the customer actually names a mileage. It used
    to default to 15 000, which meant an allowance nobody had chosen was drawn
    on their screen as though they had — see `because` for the other half of
    the same idea.
    """

    body_types: list[str] = field(default_factory=list)  # search vocabulary
    fuel: str | None = None
    transmission: str | None = None
    min_seats: int | None = None
    annual_km: int | None = None
    term_months: int = DEFAULT_TERM
    reasons: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    #: The circumstances this recommendation was actually built from, in the
    #: customer's own terms ("five of you", "mostly motorway"). This is what
    #: makes the advice legibly *theirs* rather than a generic table, so the
    #: advisor can name it and the screen can lead with it.
    because: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """True when nothing was actually derived — only questions came back.

        The caller uses this to decide whether there is anything worth showing
        the customer yet. Nothing goes on their screen before they have asked
        for a recommendation or stated a preference.
        """
        return not self.body_types and not self.fuel and not self.transmission

    def as_dict(self) -> dict[str, object]:
        return {
            "body_types": self.body_types,
            "fuel": self.fuel,
            "transmission": self.transmission,
            "min_seats": self.min_seats,
            "annual_km": self.annual_km,
            "term_months": self.term_months,
            "reasons": self.reasons,
            "because": self.because,
            "is_personal": bool(self.because),
            "next_question": self.open_questions[0] if self.open_questions else None,
            "open_questions": self.open_questions,
            "search_hint": (
                "Search with body_type = the first entry of body_types, plus the "
                "fuel and transmission above. Offer the alternatives only if the "
                "first search comes back thin."
            ),
            "how_to_say_it": (
                "This is YOUR recommendation for THIS person: say so, and name "
                "the two or three entries from `because` it came from, so they "
                "hear their own circumstances in it. Then ask them to confirm "
                "before you search on it — it is a suggestion until they agree."
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
    hobbies: str | None = None,
) -> Profile:
    """Turn use-case answers into a car profile, with a reason for every choice.

    `previous_car_body_type` is the body type of a car they have driven before
    (looked up in the listings, not guessed) — people are happiest in roughly
    the size they are used to, so it breaks ties.

    `hobbies` is whatever they said they do — cycling, a dog, skiing, towing a
    caravan. It is often the answer that actually decides the body type, and it
    is what makes the recommendation sound like it was made for them.
    """
    profile = Profile()
    use = (usage or "").strip().lower()
    road = (mostly or "").strip().lower()
    if road not in ROADS:
        road = ""
    pastimes = _hobbies(hobbies)

    # -- what this recommendation is built from ------------------------------
    # Collected before anything is derived, so the advisor can always say which
    # of THEIR answers produced the advice. No entry here that they did not
    # tell us; an empty list means we are still guessing and should not.
    if passengers is not None:
        profile.because.append(
            "it is just you" if passengers <= 1 else f"there are {passengers} of you"
        )
    if use in USES:
        profile.because.append(USES[use])
    if annual_km is not None:
        profile.because.append(f"{_km(annual_km)} km a year")
    if road:
        profile.because.append(f"mostly {road} driving")
    if can_charge is True:
        profile.because.append("you can charge at home or at work")
    elif can_charge is False:
        profile.because.append("no charger where you park")
    if carries_cargo:
        profile.because.append("you carry things")
    profile.because.extend(hobby.label for hobby in pastimes)
    if previous_car_body_type:
        profile.because.append(f"you have driven a {previous_car_body_type}")

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
        who = (
            f"there are {passengers} of you"
            if passengers is not None
            else "you are buying this for the family"
        )
        profile.reasons.append(
            f"Since {who}, the boot matters more to you than the badge — an "
            "estate gives you the most space per euro, an SUV the easier "
            "loading height."
        )
    elif use == "city":
        profile.body_types = ["compact", "sedan"]
        profile.reasons.append(
            "You said the car is for the city, and there a compact is easier to "
            "park and cheaper to run; anything larger you pay for twice."
        )
    elif use == "work":
        profile.body_types = ["van", "estate", "SUV"]
        profile.reasons.append(
            "Your car has to earn its keep, so load space is the deciding "
            "feature — everything else comes second to what fits in the back."
        )
    elif use == "travel":
        profile.body_types = ["estate", "sedan", "SUV"]
        profile.reasons.append(
            "You are planning long trips, and for those comfort on the motorway "
            "matters most — an estate or a sedan is quieter and steadier than "
            "something tall."
        )
    elif use in {"commute", "leisure"}:
        profile.body_types = ["compact", "sedan", "estate"]
        profile.reasons.append(
            f"For {USES[use]} a compact or a sedan is the sensible middle for "
            "you: cheap to run, comfortable enough for a long day."
        )
    else:
        profile.open_questions.append(
            "What will you mainly use the car for — family, commuting, work, or "
            "longer trips?"
        )

    if carries_cargo and "estate" not in profile.body_types:
        profile.body_types.insert(0, "estate")
        profile.reasons.append("You mentioned carrying things, so an estate first.")

    # -- what they actually do with it ---------------------------------------
    # A pastime never outranks a seat count — six people still need six seats —
    # but within the shapes that already fit, it is usually the answer that
    # decides between an estate and a sedan.
    may_reorder = profile.min_seats is None or profile.min_seats <= 5
    for hobby in pastimes:
        if not profile.body_types:
            profile.body_types = list(hobby.body_types)
        elif may_reorder:
            for body in reversed(hobby.body_types):
                if body in profile.body_types:
                    profile.body_types.remove(body)
                    profile.body_types.insert(0, body)
                elif len(profile.body_types) < 4:
                    profile.body_types.append(body)
        profile.reasons.append(hobby.reason)

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
    if not pastimes:
        profile.open_questions.append(
            "And what do you do at the weekend — bikes, a dog, skis, a trailer? "
            "That is usually what decides the shape of the car."
        )
    profile.open_questions.append(
        "And what would you like to spend per month — a ceiling, or a range "
        "from and to? That is what I search on."
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
