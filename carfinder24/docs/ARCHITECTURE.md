# Architecture

## What it does

A visitor opens a web page, clicks *Start chat*, and talks. The advisor leads
them from a vague idea to a specific car: what the car is *for*, what it should
look like, what condition it should be in, and what they want to spend **per
month**. It searches 45,611 real German listings by *monthly leasing rate*,
shows a shortlist on their screen while it talks, scores whether each one is a
good price, quotes the exact rate for the car they pick, summarises why that
car answers what they asked for, and emails them the offer — with the draft
leasing agreement attached if they ask for the contract itself.

## The advisory funnel

The conversation has a shape, and the shape is enforced by tools rather than
hoped for in a prompt.

| Step | What is asked | What answers it |
|---|---|---|
| 1 | Size, body type, fuel, transmission | `search_cars` |
| 2 | *"I don't know"* → what is the car FOR? Family, commute, work, trips? Can you charge at home? What have you driven? | `advise_car_type` — deterministic rules in `cars_mcp/advice.py`, with a stated reason for every part of the recommendation |
| 3 | Cosmetics: colour, body type | `search_cars(color=…)` |
| 4 | Condition: mileage, age, accidents, service history, owners | `search_cars(max_mileage_km=…, no_accident=…, …)` |
| 5 | Money: per month or outright, as a ceiling **or a range**; term and mileage tier if leasing | `leasing_options`, `search_cars(min_monthly_rate=…, max_monthly_rate=…)`, `search_cars(mode="buy")`, `leasing_quote` |
| 6 | "So here is what you chose, and why this car" | `decision_summary` — checked against the listing, not recalled |
| 7 | How to finish: nothing / email the offer / email it with the draft PDF | `closing_options`, `email_offer` |

## The three processes

```
 browser ──WebRTC──► LiveKit Cloud ──► agent worker ──HTTP/MCP──► tool server
    ▲                                    │                            │
    └────── data channel "ui" ───────────┘                     DuckDB │ SES
                                                        45,611 listings│
```

| Process | Command | Role |
|---|---|---|
| Tool server | `uv run used-car-advisor-mcp` | Owns the data and every capability. DuckDB over the Parquet snapshot + the leasing model + the deal scorer + the mailer, exposed as ten MCP tools. Start it first. |
| Agent worker | `uv run used-car-advisor dev` | The voice loop. OpenAI `gpt-realtime` does STT + reasoning + TTS in one stream; the persona's tools call the tool server and draw on the page. |
| Web client | `uv run used-car-advisor-web` | Serves the page and mints LiveKit tokens that summon *this laptop's* agent by name. |

## The ten tools

| Tool | Answers |
|---|---|
| `advise_car_type` | "I don't know what I want" — use case in, car profile out, with reasons |
| `search_cars` | "What can I get for €300 a month?" — filters and ranks by monthly rate; `mode="buy"` for outright purchase |
| `car_details` | "Tell me more about the second one" |
| `price_check` | "Is that a good deal?" — a 0.0–5.0 score against a peer group of comparable listings |
| `leasing_options` | "What terms can I have?" — and the answer to every refused choice |
| `leasing_quote` | The authoritative, bindable rate and its breakdown |
| `explain_leasing` | "Where does that number come from?" — the whole derivation, with their euros in it |
| `decision_summary` | "So what did I choose, and why this car?" |
| `closing_options` | The three ways the conversation may end |
| `email_offer` | Car summary + leasing terms, and the draft agreement as a PDF on request |

## Five decisions worth defending

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
`used_car_advisor/tools.py` does four things a raw tool cannot:

- **draws the result on the page** while the agent keeps speaking (the "ui"
  data channel) — a voice-only agent would make the customer memorise six numbers;
- **guards the model's arguments** — a spoken "about forty thousand kilometres"
  is *refused* with the tiers that do exist, not snapped to the nearest one
  (see decision 3);
- **records what the customer said** as they say it (`Consultation` in
  `state.py`), so the closing summary is built from their answers rather than
  the model's recollection of them;
- **turns a failure into a sentence** — a dead tool server costs one turn, not
  the conversation.

Cost: one hand-written wrapper per tool. Documented in `AGENT_HARNESS.md`.

**3. Terms and mileage tiers are buckets, and a wrong one is refused.**
The obvious kindness — round "about forty thousand kilometres" down to the
30,000 tier and carry on — is the expensive one: the customer finds out at the
settlement, having never agreed to it. So `cars_leasing/model.validate_choices`
refuses anything outside the buckets and returns the buckets that exist, and
nothing downstream proceeds: not the search, not the quote, not the email. The
refusal is checked twice, in the agent wrapper and again in the tool, because
either layer alone can be talked around.

The one place we *do* round is `advice.nearest_tier`, when **we** recommend an
allowance rather than the customer choosing one — and it rounds up, never down.

**4. "Is it a good deal?" is arithmetic, never an opinion — and always shown.**
`cars_deal/quality.py` builds a peer group — same make and model, same vehicle
and body type, within two years and 20,000 km — widening in fixed steps until
at least five cars are in it, and scores the listing against that group's
average price on a 0.0–5.0 scale mapped to the labels German buyers know
(*sehr guter Preis*, *guter Preis*, *fairer Preis*, …). Same snapshot, same
listing, same number, every time; the card on the screen and the verdict on
request cannot disagree, and a model that has never been asked to *judge* has
nothing to inflate. A rare car whose peer group never fills scores nothing at
all — "I cannot tell" is an allowed answer, and it is *said* rather than left
blank: the label is always rendered ("No comparison"), the score is withheld,
because 0.0 out of 5 would read as the worst price on the lot.

The verdict rides along with every surface that shows a car — the shortlist
card, `car_details`, the quote, the closing summary — not only with
`price_check`. It used to appear on search cards alone, so asking "tell me more
about the second one" redrew the card *without* the rating it just had.

**5. Partner dealers are prioritised in code, and disclosed on the card.**
Partners come first — but only *within* the cars that already match what the
customer asked for, and the customer's own ranking key still orders each group.
A partner car never enters a shortlist by being a partner car, every card
carries a "★ Partner dealer" badge, and the result set carries the disclosure
the advisor must give if asked.

One qualification, added with range search: when the customer states a budget
*range*, the shortlist is spread across it (one car per third of the band, each
the one nearest its band's middle), and partner preference then applies *within
each band* rather than across the whole shortlist. So a range search can show a
non-partner car above a partner one. The bound is unchanged — partners are still
only ever surfaced among cars that already match — but the ordering guarantee is
per-band, not global. The snapshot has no partner flag, so the
programme is derived from public reputation in `cars_mcp/partners.py`
(~15% of dealer listings); swap `PARTNER_DDL` for a contract table when there
is one.

## Latency

The MCP session is opened while the visitor is still saying hello, then reused
(`ToolClient`), so a search costs ~70 ms of database time, not a handshake.
Search results are capped at five compact rows: the model reads them aloud, so
every extra token is dead air.
