# Architecture

## What it does

A visitor opens a web page, clicks *Start chat*, and talks. The advisor asks
what they want to spend **per month**, searches 45,611 real German listings by
*monthly leasing rate*, shows a shortlist on their screen while it talks,
quotes the exact rate for the car they pick, and emails them the car summary
and the leasing agreement.

## The three processes

```
 browser ──WebRTC──► LiveKit Cloud ──► agent worker ──HTTP/MCP──► tool server
    ▲                                    │                            │
    └────── data channel "ui" ───────────┘                     DuckDB │ SES
                                                        45,611 listings│
```

| Process | Command | Role |
|---|---|---|
| Tool server | `uv run used-car-advisor-mcp` | Owns the data and every capability. DuckDB over the Parquet snapshot + the leasing model + the mailer, exposed as five MCP tools. Start it first. |
| Agent worker | `uv run used-car-advisor dev` | The voice loop. OpenAI `gpt-realtime` does STT + reasoning + TTS in one stream; the persona's tools call the tool server and draw on the page. |
| Web client | `uv run used-car-advisor-web` | Serves the page and mints LiveKit tokens that summon *this laptop's* agent by name. |

## The five tools

| Tool | Answers |
|---|---|
| `search_cars` | "What can I get for €300 a month?" — filters and ranks by monthly rate |
| `car_details` | "Tell me more about the second one" |
| `price_check` | "Is that a good deal?" — vs. comparable listings in the snapshot |
| `leasing_quote` | The authoritative, bindable rate and its breakdown |
| `email_offer` | Car summary + leasing agreement, to the address on file |

## Two decisions worth defending

**1. The leasing model runs in SQL as well as Python.**
Customers budget in euros per month, so the product has to *search* on monthly
rate — which means the rate must be a SQL expression, not a post-processing
step over 20 fetched rows. `cars_leasing/sql.py` compiles the model into DuckDB
macros generated from the same constants as `cars_leasing/model.py`, so
`WHERE monthly_rate <= 300` is a real predicate over the full table (70 ms).

The SQL rate ranks; the Python rate is what a customer is ever told and what
goes in the email. `tests/test_leasing_parity.py` asserts they agree to the
cent on real rows for all 16 term × mileage combinations, so they cannot drift.

Search also evaluates every eligibility rule in SQL, so it can only return cars
the quote step will accept — the agent can never offer a car it then can't
quote. `test_every_result_can_actually_be_quoted` locks that in.

**2. The agent wraps the MCP tools instead of exposing them raw.**
The harness supports handing the toolset straight to the model
(`Persona.mcp_tools`, still wired). We don't, because each wrapper in
`used_car_advisor/tools.py` does three things a raw tool cannot:

- **draws the result on the page** while the agent keeps speaking (the "ui"
  data channel) — a voice-only agent would make the customer memorise six numbers;
- **repairs the model's arguments** — a spoken "about forty thousand kilometres"
  is snapped to the nearest allowed tier instead of being declined;
- **turns a failure into a sentence** — a dead tool server costs one turn, not
  the conversation.

Cost: one hand-written wrapper per tool. Documented in `AGENT_HARNESS.md`.

## Latency

The MCP session is opened while the visitor is still saying hello, then reused
(`ToolClient`), so a search costs ~70 ms of database time, not a handshake.
Search results are capped at five compact rows: the model reads them aloud, so
every extra token is dead air.
