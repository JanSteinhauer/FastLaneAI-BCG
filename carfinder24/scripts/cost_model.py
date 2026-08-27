"""What one conversation with the advisor costs.

    uv run python scripts/cost_model.py

Every rate is a named constant at the top — change one and the whole model
moves. Rates are list prices as of August 2026; see docs/UNIT_ECONOMICS.md for
sources and for the derivation of the two coefficients that matter.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- rates ------------------------------------------------------------------
# OpenAI gpt-realtime-2.1, per 1M tokens
AUDIO_IN = 32.00
AUDIO_OUT = 64.00
AUDIO_CACHED = 0.40
TEXT_CACHED = 0.40

# The Realtime API tokenises speech at a fixed rate.
TOK_PER_SEC_IN = 10  # 600 tokens per minute of customer speech
TOK_PER_SEC_OUT = 20  # 1200 tokens per minute of agent speech

# LiveKit Cloud, per minute
LK_AGENT_MIN = 0.010  # agent session minute
LK_PARTICIPANT_MIN = 0.0005  # the human's WebRTC minute
LK_BANDWIDTH_GB = 0.12  # downstream; upstream is free
AUDIO_MBPS = 0.032 / 8  # ~32 kbps Opus
VIDEO_MBPS = 1.0 / 8  # ~1 Mbps avatar video

# Tavus conversational video
TAVUS_MIN = 0.37
TAVUS_MIN_BILLED = 0.5  # 30-second minimum per conversation

# Amazon SES
SES_PER_EMAIL = 0.0001

# Our fixed context: system prompt + the five tool schemas, re-sent every turn
# and cached after the first. Measured, not guessed.
FIXED_CONTEXT_TOKENS = 1711


@dataclass
class Conversation:
    name: str
    turns: int  # exchanges (customer question + agent answer)
    customer_sec: float  # seconds the customer speaks, per turn
    agent_sec: float  # seconds the agent speaks, per turn
    session_min: float  # wall-clock minutes the room is open
    emails: int = 1
    avatar: bool = False

    @property
    def speech_in(self) -> float:
        return self.turns * self.customer_sec

    @property
    def speech_out(self) -> float:
        return self.turns * self.agent_sec

    def openai(self) -> dict[str, float]:
        fresh_in = self.speech_in * TOK_PER_SEC_IN * AUDIO_IN / 1e6
        out = self.speech_out * TOK_PER_SEC_OUT * AUDIO_OUT / 1e6
        # Every turn re-sends the whole conversation so far. That is quadratic
        # in turns — and irrelevant, because it is cached at 1/80th the price.
        per_turn = self.customer_sec * TOK_PER_SEC_IN + self.agent_sec * TOK_PER_SEC_OUT
        history = per_turn * self.turns * (self.turns - 1) / 2
        cached = history * AUDIO_CACHED / 1e6
        context = FIXED_CONTEXT_TOKENS * self.turns * TEXT_CACHED / 1e6
        return {"audio in": fresh_in, "audio out": out,
                "cached history": cached, "prompt + tools": context}

    def livekit(self) -> dict[str, float]:
        mbps = AUDIO_MBPS + (VIDEO_MBPS if self.avatar else 0)
        gb = mbps * 60 * self.session_min / 1000
        return {"agent session": self.session_min * LK_AGENT_MIN,
                "participant": self.session_min * LK_PARTICIPANT_MIN,
                "bandwidth": gb * LK_BANDWIDTH_GB}

    def tavus(self) -> dict[str, float]:
        if not self.avatar:
            return {"avatar": 0.0}
        return {"avatar": max(TAVUS_MIN_BILLED, self.session_min) * TAVUS_MIN}

    def email(self) -> dict[str, float]:
        return {"email": self.emails * SES_PER_EMAIL}

    def total(self) -> float:
        return sum(sum(part.values())
                   for part in (self.openai(), self.livekit(), self.tavus(), self.email()))


SCENARIOS = [
    Conversation("Short — 3 questions, decisive", 3, 5, 8, 1.5),
    Conversation("Median — 6 questions", 6, 6, 10, 3.0),
    Conversation("Long — 10 questions, wandering", 10, 7, 12, 6.0),
]


def report() -> None:
    for avatar in (False, True):
        head = "WITH TAVUS AVATAR" if avatar else "VOICE ONLY"
        print(f"\n{head}\n{'=' * 74}")
        for base in SCENARIOS:
            c = Conversation(base.name, base.turns, base.customer_sec, base.agent_sec,
                             base.session_min, base.emails, avatar)
            print(f"\n{c.name}  ({c.turns} turns, {c.speech_in:.0f}s customer / "
                  f"{c.speech_out:.0f}s agent, {c.session_min:.1f} min session)")
            for label, parts in (("OpenAI", c.openai()), ("LiveKit", c.livekit()),
                                 ("Tavus", c.tavus()), ("AWS", c.email())):
                sub = sum(parts.values())
                if sub == 0:
                    continue
                detail = ", ".join(f"{k} ${v:.5f}" for k, v in parts.items() if v)
                print(f"  {label:<9} ${sub:>8.5f}   {detail}")
            print(f"  {'TOTAL':<9} ${c.total():>8.5f}   "
                  f"= ${c.total() * 1000:.2f} per 1 000 conversations")


if __name__ == "__main__":
    report()
    print("\n" + "=" * 74)
    med = Conversation("median", 6, 6, 10, 3.0)
    med_av = Conversation("median", 6, 6, 10, 3.0, avatar=True)
    print(f"MEDIAN INTERACTION   voice only ${med.total():.4f}   "
          f"with avatar ${med_av.total():.4f}   "
          f"(avatar is {med_av.total() / med.total():.0f}x)")
