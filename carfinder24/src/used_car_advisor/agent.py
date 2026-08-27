from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli, mcp
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession, RunContext
from livekit.plugins import openai
from openai.types import realtime as openai_realtime

from used_car_advisor.identity import agent_name
from used_car_advisor.prompts import WELCOME_PROMPT

logger = logging.getLogger("used-car-advisor")
logger.setLevel(logging.INFO)

load_dotenv()

# The MCP server (src/cars_mcp) runs standalone — start it before the agent:
# `uv run used-car-advisor-mcp`. MCP_URL must be set in .env; fail fast and
# loud here rather than silently starting an agent that cannot use tools.
MCP_URL = os.getenv("MCP_URL") or ""
if not MCP_URL:
    raise RuntimeError(
        "MCP_URL is not set — add it to .env "
        "(default server: MCP_URL=http://127.0.0.1:8990/mcp) "
        "and start the MCP server first: uv run used-car-advisor-mcp"
    )


@dataclass
class UserData:
    """Shared plumbing for persona transfers — the conversation itself is the
    only domain state; personas read everything else from the chat context."""

    personas: dict[str, Agent] = field(default_factory=dict)
    prev_agent: Agent | None = None
    ctx: JobContext | None = None


RunContext_T: TypeAlias = RunContext[UserData]


async def push_to_frontend(context: RunContext_T, payload: dict) -> None:
    """Show content in the web frontend while the agent keeps talking.

    payload: {"type": "cars", "cars": [...]} renders listing cards;
             {"type": "text", "text": "..."} renders a plain text bubble.
    Silently does nothing when no frontend is connected.
    """
    userdata = context.userdata
    if userdata.ctx is None or userdata.ctx.room is None:
        return
    try:
        await userdata.ctx.room.local_participant.send_text(
            json.dumps(payload), topic="ui"
        )
    except Exception:
        # Frontend display is best-effort; never break the voice flow.
        logger.debug("push_to_frontend failed", exc_info=True)


# Keep in sync with the PERSONAS registry below.
PersonaName: TypeAlias = Literal["welcome"]


@function_tool
async def switch_persona(context: RunContext_T, name: PersonaName) -> Agent | str:
    """Hand the conversation to another persona from the PERSONAS registry.

    The target must be listed in the current persona's `transfers` allowlist.

    Announce the handover to the visitor in one short sentence AND call this
    tool in the same response. Never switch silently — and never announce a
    handover without calling this tool: only the call transfers the chat,
    saying it out loud does nothing.
    """
    current = context.session.current_agent
    allowed = current.persona.transfers if isinstance(current, PersonaAgent) else ()
    if name not in allowed:
        return f"You cannot switch to '{name}' from here — only to: {allowed}."
    # NB: don't call session.say() here — RealtimeModel doesn't support it.
    # The target persona's on_enter greets the visitor via generate_reply().
    context.userdata.prev_agent = current
    return context.userdata.personas[name]


# ---------------------------------------------------------------------------
# Personas — an agent is defined by its prompt, voice, and tools. Adding a
# persona means adding an entry here (plus its name in PersonaName above,
# and the new persona's name in the `transfers` of whoever may reach it).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Persona:
    """Everything that distinguishes one agent persona from another."""

    prompt: str
    voice: str  # gpt-realtime voice name
    color: str  # aura color in the web frontend (hex)
    transfers: tuple[str, ...] = ()  # personas switch_persona may reach from here
    tools: tuple = ()  # extra function tools beyond switch_persona
    # Tools this persona may use from the MCP server — list the names of the
    # tools you write in cars_mcp/server.py to give this persona access.
    mcp_tools: tuple[str, ...] = ()


PERSONAS: dict[str, Persona] = {
    "welcome": Persona(
        prompt=WELCOME_PROMPT,
        # `cedar` is a warm, masculine voice; other gpt-realtime voices
        # include marin, sage, alloy, ash, ballad, coral, echo, shimmer, verse.
        voice="cedar",
        color="#00E0B5",  # bright teal
        # A tool you add in cars_mcp/server.py is NOT picked up automatically:
        # list its name here to let this persona use it.
        mcp_tools=(),
    ),
}


def _realtime_llm(voice: str) -> openai.realtime.RealtimeModel:
    """Single OpenAI Realtime model — handles STT, LLM, and TTS in one stream."""
    return openai.realtime.RealtimeModel(
        model="gpt-realtime",
        voice=voice,
        # Laptop mics + speaker playback: without these, the acoustic VAD
        # picks up echo/noise as user turns and the agent answers the silence
        # ("No problem, take your time...") or interrupts its own greeting.
        input_audio_noise_reduction="near_field",
        turn_detection=openai_realtime.realtime_audio_input_turn_detection.SemanticVad(
            type="semantic_vad",
            eagerness="auto",
            create_response=True,
            interrupt_response=True,
        ),
    )


class PersonaAgent(Agent):
    """The one agent class — a persona config decides what it is.

    On transfer the full chat context is carried over, so the new persona
    infers everything (including which car is being discussed) from the
    conversation itself; there is no side channel.
    """

    def __init__(self, name: str, persona: Persona) -> None:
        self.persona = persona
        self._label = f"{name.title()}Agent"  # shown by the web frontend
        tools = [switch_persona, *persona.tools]
        if persona.mcp_tools:
            # The data tools live in the standalone MCP server; each persona
            # sees only the tools it needs. If the server isn't running, the
            # agent comes up without data tools and the persona can't use them.
            tools.append(
                mcp.MCPToolset(
                    id=name,
                    mcp_server=mcp.MCPServerHTTP(
                        url=MCP_URL, allowed_tools=list(persona.mcp_tools)
                    ),
                )
            )
        super().__init__(
            instructions=persona.prompt,
            llm=_realtime_llm(persona.voice),
            tools=tools,
        )

    async def on_enter(self) -> None:
        logger.info("Entering %s", self._label)

        userdata: UserData = self.session.userdata
        if userdata.ctx and userdata.ctx.room:
            # The web frontend shows the label and tints the aura with the
            # persona color (attribute "agent_color").
            await userdata.ctx.room.local_participant.set_attributes(
                {"agent": self._label, "agent_color": self.persona.color}
            )

        # Carry the whole conversation into this persona — its instructions
        # (the persona prompt) replace the previous one's automatically.
        if userdata.prev_agent:
            await self.update_chat_ctx(userdata.prev_agent.chat_ctx.copy())
        self.session.generate_reply()


async def entrypoint(ctx: JobContext) -> None:
    # Connect to the LiveKit room BEFORE starting the session — without this
    # the agent has no audio track to publish into and the caller hears silence.
    await ctx.connect()

    userdata = UserData(ctx=ctx)
    userdata.personas.update(
        {name: PersonaAgent(name, persona) for name, persona in PERSONAS.items()}
    )

    session = AgentSession[UserData](userdata=userdata)

    await session.start(agent=userdata.personas["welcome"], room=ctx.room)


def main() -> None:
    # Explicit dispatch: this worker only serves rooms whose token summons
    # THIS laptop's agent by name (web.py mints those) — several people can
    # run workers on one LiveKit project without grabbing each other's chats.
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name=agent_name()))


if __name__ == "__main__":
    main()
