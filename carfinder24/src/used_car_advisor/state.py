"""Session state shared by the agent and its tools.

The conversation itself is still the domain state — personas read what car is
being discussed straight out of the chat context. What lives here is plumbing
(the room, the persona registry, the tool connection) plus one thing that must
not be left to recall: `Consultation`.

Why: the advisory ends with "here is what you chose and why this car". If that
summary is assembled from what the model *remembers* saying, it will
occasionally summarise a budget nobody named or a colour nobody asked for. So
every tool call records the facts it was given as it goes, and the summary is
built from the record. The model can still add to it, but it cannot invent the
parts the customer actually stated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

from livekit.agents import JobContext
from livekit.agents.voice import Agent, RunContext

if TYPE_CHECKING:
    from used_car_advisor.mcp_client import ToolClient


@dataclass
class Consultation:
    """What the customer has told us so far, accumulated across tool calls."""

    used_for: str | None = None
    must_have: str | None = None
    body_type: str | None = None
    fuel: str | None = None
    transmission: str | None = None
    color: str | None = None
    max_mileage_km: int | None = None
    budget_monthly_eur: float | None = None  # the ceiling they named
    min_budget_monthly_eur: float | None = None  # the floor, if they gave a range
    finance: str = "lease"  # "lease" or "buy"
    term_months: int | None = None
    annual_km: int | None = None
    down_payment: int = 0
    ref: str | None = None  # the car currently on the table

    # What WE recommended, kept strictly apart from what they told us. A
    # suggestion that leaks into the fields above comes back at the close as
    # "the estate you wanted" — a choice the customer never made, quoted back
    # to them as their own. Only advise_car_type writes these.
    suggested_body_type: str | None = None
    suggested_fuel: str | None = None
    suggested_transmission: str | None = None

    def record(self, **values: Any) -> None:
        """Remember the values that were actually supplied; ignore the rest.

        Later answers win — customers revise ("actually, make it blue") — but a
        `None` never erases something they already said.
        """
        for key, value in values.items():
            if value is not None and hasattr(self, key):
                setattr(self, key, value)

    def as_kwargs(self) -> dict[str, Any]:
        """The recorded facts, ready to hand to the summary tool."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class UserData:
    personas: dict[str, Agent] = field(default_factory=dict)
    prev_agent: Agent | None = None
    ctx: JobContext | None = None
    tools: ToolClient | None = None  # connection to the MCP tool server
    consultation: Consultation = field(default_factory=Consultation)


RunContext_T: TypeAlias = RunContext[UserData]
