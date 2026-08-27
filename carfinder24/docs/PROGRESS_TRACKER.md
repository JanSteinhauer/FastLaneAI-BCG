# The progress strip, and how it connects to the MCP

## The problem it solves

A voice call has no scrollback. Ten seconds after the customer says *"twenty
thousand kilometres a year"* there is nothing on screen confirming the advisor
heard it — so they repeat themselves, or they don't and find out at the quote.
Worse, in a live demo the room cannot tell whether the agent understood
anything until a card finally appears.

So the top of the page carries a strip with the two phases of the journey, each
filling in as the advisor establishes a point:

```
┌ The car ──────────────── 4/12 ┐ ┌ The leasing ──────────── 8/9 ┐
│ ▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░ │ │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░ │
│ (Type estate) (Fuel diesel)   │ │ (Budget €300/month)          │
│ (Colour Grey) (Power 120 hp)  │ │ (Usage 20 000 km/year)       │
│  Make   Model   Gearbox …     │ │ (Term 36 months) (Rate €144) │
└───────────────────────────────┘ └ (Finance 6.49 %) (Residual)──┘
                  Ford Focus Turnier Titanium
```

Filled slots are solid and carry their value; unfilled ones are dashed outlines,
so the customer can see what the advisor still needs. The stage in focus is
bright, the other dimmed.

## How the MCP knows what is being talked about

Three ways to answer "what has the conversation established?", and the one we
chose is the cheap one.

**1. Ask the model to declare it.** A `set_criteria` tool the advisor calls
after each exchange. Costs a tool call per turn — latency in a voice call where
latency is the product — and it can be forgotten, so the strip silently drifts
out of sync with what was actually said.

**2. Read the transcript.** A second model summarising the conversation into
slots. Another inference per turn, another thing to be wrong, and it can
hallucinate a constraint the customer never gave.

**3. Derive it from the tool calls.** ← what this does.

When the advisor calls `search_cars(max_monthly_rate=300, body_type="estate",
fuel="diesel", annual_km=20000)`, the criteria *are* those arguments. The model
already decided them, already passed them, and the tool already validated them.
Reading them costs nothing, cannot be forgotten, and cannot describe a state the
system is not actually in — if the strip says "diesel", a diesel filter really
was applied.

The same holds for results: `leasing_quote` returns the monthly rate, the APR
and the residual, so those fill themselves in the moment they become true.

## Where the MCP comes in

The **vocabulary** lives with the data, not in the browser and not in the agent.

`src/cars_mcp/criteria.py` owns the slot table: which slots exist, which of the
two stages each belongs to, what a customer calls it, and how to format its
value. It sits beside `guards.py`, which already knows that `body_type="estate"`
means `Station wagon` — the same kind of knowledge, in the same layer.

It is exposed as an MCP tool:

```python
@mcp.tool
def describe_criteria(criteria: dict) -> dict:
    """Render what the conversation has established as two fillable stages."""
```

The full path of one update:

```
model calls find_cars(max_monthly_rate=300, body_type="estate", …)
        │
        ▼
tools.py  ── calls MCP search_cars ──────────────► cars_mcp/server.py
        │                                                  │
        │   _remember(**those same arguments)               │
        │        merges into userdata.criteria              │
        │        (empty values dropped, so a later          │
        │         call cannot blank a filled slot)          │
        ▼                                                   │
     calls MCP describe_criteria(criteria) ─────────────────┤
        │                                    criteria.py maps
        │                                    keys → stage, label,
        │◄────── two stages of slots ─────── formatted value
        ▼
ui.push_progress()  →  LiveKit data channel, topic "progress"
        │
        ▼
frontend ProgressStrip  →  draws it. No logic in the browser.
```

Two properties worth keeping:

- **The browser is a dumb renderer.** Values arrive pre-formatted (`€300 /
  month`, `20 000 km / year`), so what is on the strip and what the advisor says
  out loud come from one place and cannot drift.
- **Its own topic.** The strip is sent on `"progress"`, not `"ui"`, so updating
  it never replaces the card the customer is currently reading.

## Why a tool and not just private code

`describe_criteria` could have been a local function — it touches no data. Making
it an MCP tool buys three things:

1. **One vocabulary.** Anything that talks to the tool server — the agent, a
   second agent, Claude Code during development, a future web UI — describes the
   conversation identically.
2. **Testability from outside.** `uv run python -c` against the running server
   renders any conversation state without booting a voice session.
3. **It is where the knowledge belongs.** The layer that knows an "estate" is a
   `Station wagon` is the layer that should know a customer calls `annual_km`
   their *usage*.

The cost is one local HTTP round trip per tool call, on an already-open session
— about two milliseconds, off the speech path.

## Adding a slot

One line in `SLOTS` in `src/cars_mcp/criteria.py`:

```python
"upholstery": ("car", "Interior", _plain),
```

…and pass it in the `_remember(...)` call of whichever tool learns it. The strip
picks it up; the browser needs no change and no rebuild.

Put results-only values — things the customer cannot ask for, like the residual
value — in `DERIVED`, so an empty one is hidden rather than shown as a gap the
advisor failed to fill.

## When it fails

The strip is a nicety and is written to behave like one. If `describe_criteria`
errors or the tool server is unreachable, `_remember` returns quietly and the
conversation continues with a stale strip. A malformed update is ignored by the
browser rather than blanking what is on screen. Nothing about the strip can cost
you a turn.

## Where this would go next

- **Server-side session state.** Today the criteria live in the agent process
  (`UserData.criteria`). Moving them behind the MCP — keyed by session — would
  let a handover to a second persona, or a reconnect after a dropped call, pick
  the conversation up exactly where it was.
- **Slots as an MCP resource.** `describe_criteria` is a tool because the agent
  calls it. The slot *table* is really a resource — publishing it as one would
  let a frontend fetch the vocabulary at load and render slots it has never seen.
- **Gaps as prompts.** The empty slots are a to-do list. The advisor could be
  handed "still open: gearbox, mileage" and use it to ask the one question that
  most narrows the search, instead of whatever comes to mind.
