from __future__ import annotations

import logging
import os
from typing import Literal, TypeAlias

from dotenv import load_dotenv
from livekit.agents import (
    JobContext,
    RoomOutputOptions,
    WorkerOptions,
    cli,
    mcp,
)
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import openai
from openai.types import realtime as openai_realtime

from used_car_advisor.identity import agent_name
from used_car_advisor.mcp_client import ToolClient
from used_car_advisor.prompts import ADVISOR_PROMPT
from used_car_advisor.state import RunContext_T, UserData
from used_car_advisor.tools import ADVISOR_TOOLS

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


# Keep in sync with the PERSONAS registry below.
PersonaName: TypeAlias = Literal["advisor"]


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
#
# One persona on purpose: the whole journey (search → advise → quote → email)
# is one continuous conversation, and every handover costs a turn of latency
# and a chance to lose the thread. The registry stays because it is the
# harness — see docs/AGENT_HARNESS.md for when to add a second persona.
# ---------------------------------------------------------------------------

from dataclasses import dataclass  # noqa: E402  (kept next to the registry it serves)


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
    # This advisor calls MCP through used_car_advisor.tools instead, so it can
    # draw results on the web page; leave empty unless you want the model to
    # talk to the tool server unmediated.
    mcp_tools: tuple[str, ...] = ()


PERSONAS: dict[str, Persona] = {
    "advisor": Persona(
        prompt=ADVISOR_PROMPT,
        # `cedar` is a warm, masculine voice; other gpt-realtime voices
        # include marin, sage, alloy, ash, ballad, coral, echo, shimmer, verse.
        voice="cedar",
        color="#00E0B5",  # bright teal
        tools=ADVISOR_TOOLS,
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
        # switch_persona only exists for personas that can actually transfer —
        # a tool the model can never use successfully is a tool it can misfire.
        tools = [*persona.tools]
        if persona.transfers:
            tools.insert(0, switch_persona)
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


async def _start_avatar(session: AgentSession, ctx: JobContext, persona_key: str) -> bool:
    """Cherry on top: give the advisor a face (Tavus), if configured.

    Off unless USE_AVATAR is set. Failure is never fatal — a broken avatar must
    not cost the demo its voice, so we fall back to audio-only and say so in
    the log. The participant identity matches what the frontend looks for.
    """
    from livekit.plugins import tavus  # imported lazily: optional dependency path

    replica_id = os.getenv("TAVUS_REPLICA_ID") or "rf4703150052"  # stock replica "Charlie"
    persona_id = os.getenv("TAVUS_PERSONA_ID") or None
    kwargs: dict[str, object] = {
        "replica_id": replica_id,
        "avatar_participant_identity": f"tavus-avatar-{persona_key}",
        "avatar_participant_name": "CarFinder24 Advisor",
    }
    if persona_id:
        kwargs["persona_id"] = persona_id
    try:
        avatar = tavus.AvatarSession(**kwargs)  # type: ignore[arg-type]
        await avatar.start(session, room=ctx.room)
        logger.info("Tavus avatar started (replica %s)", replica_id)
        return True
    except Exception:
        logger.exception("Tavus avatar failed to start — continuing audio-only")
        return False


async def entrypoint(ctx: JobContext) -> None:
    # Connect to the LiveKit room BEFORE starting the session — without this
    # the agent has no audio track to publish into and the caller hears silence.
    await ctx.connect()

    userdata = UserData(ctx=ctx)
    userdata.personas.update(
        {name: PersonaAgent(name, persona) for name, persona in PERSONAS.items()}
    )

    # Open the tool session while the visitor is still saying hello, so the
    # first search does not pay for the handshake.
    userdata.tools = ToolClient(MCP_URL)
    try:
        await userdata.tools.connect()
    except Exception:
        logger.exception("MCP tool server unreachable at %s — tools will retry", MCP_URL)
    ctx.add_shutdown_callback(userdata.tools.aclose)

    session = AgentSession[UserData](userdata=userdata)

    avatar_on = False
    if os.getenv("USE_AVATAR", "").strip().lower() in {"1", "true", "yes", "on"}:
        avatar_on = await _start_avatar(session, ctx, "advisor")

    await session.start(
        agent=userdata.personas["advisor"],
        room=ctx.room,
        # With an avatar, audio is published by the avatar worker (lip-synced);
        # publishing it twice would double the voice.
        room_output_options=RoomOutputOptions(audio_enabled=not avatar_on),
    )


def main() -> None:
    # Explicit dispatch: this worker only serves rooms whose token summons
    # THIS laptop's agent by name (web.py mints those) — several people can
    # run workers on one LiveKit project without grabbing each other's chats.
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name=agent_name()))


if __name__ == "__main__":
    main()
