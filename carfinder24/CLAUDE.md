# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A voice advisor for CarFinder24 (used cars, German market). A visitor talks to it
in the browser; it leads them from a vague idea to a specific car, searches ~46k
real AutoScout24 listings **by monthly leasing rate**, scores the deal, quotes a
binding rate, and emails the offer. Built for a live demo — a broken demo is the
worst outcome, so prefer changes that keep the three processes startable.

Deeper background lives in `docs/` (ARCHITECTURE, AGENT_HARNESS, SECURITY,
DEMO_SCRIPT, PITCH, ROLES). Read `docs/AGENT_HARNESS.md` before touching the
agent or its tools.

## Commands

```bash
uv sync                                   # install (Python 3.13, uv-managed)

# The stack — three processes, three terminals, IN THIS ORDER:
uv run used-car-advisor-mcp               # 1  tool server, http://127.0.0.1:8990/mcp
uv run used-car-advisor dev               # 2  voice agent worker
uv run used-car-advisor-web               # 3  web page, http://localhost:8080

uv run pytest tests -q                    # 128 tests, ~no network, nothing is emailed
uv run pytest tests/test_closing.py -q                       # one file
uv run pytest tests/test_agent_side.py::test_what_the_customer_said_is_kept  # one test
uv run pytest tests -q -k leasing         # by name

uv run ruff check .                       # ruff is a dev dep; no [tool.ruff] config
```

In VS Code, `Ctrl+Shift+B` runs the prepared task that starts all three in order
(`.vscode/tasks.json`).

`--port` works on the web and tool servers. If the *tool* server moves, update
`MCP_URL` in `.env` and restart the agent.

**There is no auto-reload.** Changed a tool → restart the tool server. Changed a
prompt/persona/wrapper → restart the agent. Then start a *fresh* chat in the browser.

`.env` (copy from `.env.example`): `LIVEKIT_*` (transport), `OPENAI_API_KEY`
(gpt-realtime does STT+LLM+TTS in one stream), `MCP_URL` (required — the agent
raises at import if unset), `AWS_*`/`EMAIL_RECIPIENT` (SES), plus two demo
switches: `USE_AVATAR=1` (Tavus face) and `DEMO_INJECTION=1` (plants a hostile
listing for the security demo).

## Architecture

Two halves that only meet over MCP/HTTP:

- `src/used_car_advisor/` — **agent side.** LiveKit worker, persona registry,
  prompt, the nine voice-facing tool wrappers, the "ui" data channel, session state.
- `src/cars_db|cars_deal|cars_leasing|cars_mailer|cars_mcp/` — **domain side.**
  Owns the data and every capability, exposed as ten MCP tools by
  `cars_mcp/server.py`. Nothing here imports `used_car_advisor`; tests call these
  functions directly.

`cars_db.CarsDB` loads `data/autoscout24_de.parquet` into an in-memory DuckDB
table `ads`, then disables filesystem access. `cars_mcp.server.get_db()` is
`lru_cache`d and extends that connection at startup with the leasing macros
(`cars_leasing/sql.py`) and the partner-dealer table (`cars_mcp/partners.py`).

### The tool layer is doubled on purpose

Every capability exists twice: an MCP tool in `cars_mcp/server.py` (the real
work) and a thin wrapper in `used_car_advisor/tools.py` that the model actually
calls. The wrapper is what draws the result on the page, re-checks the
customer's leasing choices, records what they said, and turns a failure into a
sentence. Adding a capability means editing **both** files:

1. `@mcp.tool` in `cars_mcp/server.py`; bind every caller value as a `$param`;
   keep the result small (it is spoken aloud); write the docstring *for the model*.
2. A wrapper in `used_car_advisor/tools.py`, listed in `ADVISOR_TOOLS`. A tool
   missing from that tuple does not exist as far as the model is concerned.

The unmediated path (`Persona.mcp_tools` → `mcp.MCPToolset`) is still wired in
`PersonaAgent.__init__` but unused; using it loses the screen and the guards.

### Invariants worth not breaking

- **SQL/Python leasing parity.** All model constants live in
  `cars_leasing/model.py`; `cars_leasing/sql.py` *generates* the DuckDB macros
  from them. Never hardcode a rate constant in the SQL — `tests/test_leasing_parity.py`
  asserts the two agree to the cent across all 16 term × mileage combinations.
  The SQL rate only ranks and filters; `compute_quote` is the only rate a
  customer is ever told.
- **`search_cars(mode="lease")` evaluates the full eligibility rule in SQL**
  (`lease_eligible`), so a searched car can never fail at the quote step.
- **A stated budget range is honoured at both ends.** `search_cars` takes
  `min_monthly_rate` as well as `max_monthly_rate` (and `min_price`/`max_price`
  for outright purchase), and the wrapper exposes both — a ceiling alone plus
  the cheapest-first default is what made an €800–1300 ask return €95 cars.
  When a floor is given and `sort` is still `"rate"`, results are **spread**
  across the band (one per `ntile`, each nearest its band's middle), and
  partner preference becomes per-band rather than global.
- **A recommendation is not a choice.** `advise_car_type` writes only
  `suggested_*` fields on `Consultation`; nothing is drawn on the customer's
  screen until something was actually derived (`tools._has_recommendation`),
  and `decision_summary` reports suggestions in their own block. Advice carries
  a `because` list — the customer's own circumstances — which is what makes it
  legibly personal.
- **The price rating is always visible** — shortlist card, `car_details`,
  `leasing_quote` and `decision_summary` all carry `deal_label`, rendered by
  the single `ui._rating`. No peer group means the label still shows
  ("No comparison") with `deal_score = None`; never 0.0, which would read as
  the worst price rather than as "cannot tell".
- **The product speaks English.** Every label, rating, quote, email, PDF and
  filename is English; only the listing data itself (titles, seller prose,
  equipment names) is German, and it is scrubbed rather than translated.
  `tests/test_tools.py::test_nothing_the_customer_sees_is_written_in_german`
  guards this, including the built frontend bundle.
- **Terms and mileage tiers are buckets, never rounded.** `validate_choices` in
  the tool and `_check_choices` in the wrapper both refuse an out-of-bucket value
  and return the buckets that exist; nothing downstream proceeds. The only place
  rounding is allowed is `advice.nearest_tier` (and it rounds up).
- **Every judgement is arithmetic**, never phrased by the model: the deal score
  (`cars_deal/quality.py`, deterministic peer group + 0.0–5.0 scale, and "not
  enough peers" is an allowed answer), the rate, the explanation.
- **Partner dealers sort first only within cars that already match**
  (`ORDER BY is_partner DESC, <customer's key>`), and every card carries the badge.
- **The email recipient is fixed by `EMAIL_RECIPIENT`.** `email_offer` takes no
  address; the tool also dedupes and caps sends per process.
- **Listing descriptions are hostile input.** `cars_mcp/guards.py` scrubs them on
  the way out to the model (`safe_snippet`) and validates enums on the way in.
- **The closing summary comes from `Consultation` (`state.py`), not recall** —
  wrappers record what the customer stated as they state it, and
  `as_kwargs()` is handed straight to `decision_summary` (their names must line up).

### Frontend

`frontend/` is a pre-built, committed esbuild bundle (`frontend/dist/app.js`) —
participants never need Node. `used_car_advisor/ui.py` pushes JSON over the
LiveKit data channel topic `"ui"`, and `frontend/src/main.jsx` understands only
four payload types: `cars`, `quote`, `sent`, `text` (most panels reuse the
`quote` label/value shape deliberately). **A new payload shape means rebuilding
the bundle**: `cd frontend && npm ci && npm run build`, and commit `dist/`.
Anything expressible as extra `rows` needs no rebuild — that is why most panels
reuse the `quote` shape.

Each laptop gets a stable agent name (`used_car_advisor/identity.py`); the web
server mints tokens that summon exactly that name, so several people can share
one LiveKit project. Don't make it random.
