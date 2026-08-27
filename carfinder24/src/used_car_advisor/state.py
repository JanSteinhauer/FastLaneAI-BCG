"""Session state shared by the agent and its tools.

The conversation itself is the domain state — personas read what car is being
discussed straight out of the chat context. This holds only plumbing: the room
(so tools can draw on the web page) and the persona registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

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


RunContext_T: TypeAlias = RunContext[UserData]
