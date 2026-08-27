"""Session state shared by the agent and its tools.

The conversation itself is the domain state — personas read what car is being
discussed straight out of the chat context. This holds only plumbing: the room
(so tools can draw on the web page) and the persona registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

from livekit.agents import JobContext
from livekit.agents.voice import Agent, RunContext

if TYPE_CHECKING:
    from used_car_advisor.mcp_client import ToolClient


@dataclass
class UserData:
    personas: dict[str, Agent] = field(default_factory=dict)
    prev_agent: Agent | None = None
    ctx: JobContext | None = None
    tools: "ToolClient | None" = None  # connection to the MCP tool server
    # The last set of search_cars filters actually in effect, so a follow-up
    # search ("show me something cheaper") keeps SUV/diesel/etc. without the
    # model having to re-state every earlier filter from memory. Merged, not
    # replaced, in used_car_advisor.tools.find_cars.
    last_filters: dict[str, Any] = field(default_factory=dict)


RunContext_T: TypeAlias = RunContext[UserData]
