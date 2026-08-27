# Adoption: how to get it, how to measure it

Two different things get called adoption, and they need different tactics:

1. **Visitor adoption** — does someone on carfinder24.de actually talk to the
   advisor instead of clicking filters?
2. **Dealer adoption** — does a dealer treat the resulting offer as a lead worth
   calling back?

The first is our funnel problem. The second decides whether the first is worth
solving. Optimise 1, but instrument 2 from the start, or we will scale something
nobody downstream acts on.

## Start with why it fails by default

A voice widget on a car site has five hard barriers, in order of how many people
they cost us:

1. **Nobody wants to "talk to an AI".** The label on the button is a bigger
   lever than anything inside the product.
2. **Microphone permission is a wall.** A browser prompt with the word "record"
   in it, before any value has been demonstrated.
3. **People are not alone.** Half of car browsing happens on a train, in an
   office, next to a sleeping child. Voice is socially unavailable even when
   technically available.
4. **The familiar path is right there.** Filters work. They are bad, but they are
   understood, and switching costs a click into the unknown.
5. **Distrust of a salesman.** "Will it push me toward whatever pays it most?"

Notice that four of the five happen **before the first word is spoken**. Almost
all of our adoption work is upstream of the agent, which is good news: the agent
is the part that already works.

## Levers, cheapest and biggest first

**1. Trigger on failure, not on arrival.**
Do not put a floating button on the homepage. Offer the advisor at the exact
moment the filters fail: zero results, the fifth filter change, the third sort,
a price slider dragged twice. Those are people who have proven the current tool
is not answering their question. Intent is highest at the moment of frustration.

**2. Put the outcome on the button, never the technology.**
Not "Talk to our AI assistant". Try **"What can I get for €300 a month?"** —
that is the product's actual promise, it is a question the site cannot otherwise
answer, and it presumes no knowledge of what is behind it.

**3. Let people type.** The single biggest unlock. Half of our traffic cannot
speak out loud, and today they simply leave. LiveKit already supports text input
into the same session (`RoomInputOptions(text_enabled=True)`) — the same agent,
the same tools, the same cards, no microphone permission, no social barrier.
Voice becomes the upgrade, not the entry fee.

**4. Answer the first question before asking for anything.**
No mic prompt, no sign-in, no form until the visitor has seen one real shortlist
appear. Value first, permission second — the permission dialog converts far
better after the product has proved itself.

**5. Warm-start from the filters they already set.**
If they have already chosen "estate, diesel, under €20,000", the advisor should
open knowing it. We already model this: the criteria the progress strip tracks
can be seeded from the URL query rather than re-asked. Nothing annoys like being
asked what you just typed.

**6. Make the email the second session.**
The offer that lands in the inbox is our only re-entry point. It should carry a
link that reopens the conversation with the car and terms intact — "still
thinking about the Focus?" A voice product with no memory across sessions is a
one-night stand.

**7. Show, do not tell.** A muted three-second loop of a real shortlist appearing
as someone speaks, on the entry point itself. Voice products are impossible to
imagine and trivial to recognise.

**8. Dealer side: hand over the transcript.** A lead that arrives with budget,
mileage, term, down payment and the car already chosen is visibly better than a
form fill. Say so in the handover — dealer adoption is a packaging problem
before it is a quality problem.

## The funnel, and what to measure at each step

| # | Step | Metric | Why it matters | Benchmark / target |
|---|---|---|---|---|
| 1 | Advisor offered | **Exposure rate** — sessions shown an entry point | Denominator for everything | 100% of qualifying sessions |
| 2 | Started | **Start rate** | The button, the moment, the copy | Chat widgets run **5–15%**; voice-first, expect 3–8% |
| 3 | Input granted | **Mic-grant rate** / text fallback share | Isolates the permission wall from disinterest | Target > 70%; the gap is the case for text |
| 4 | First useful turn | **Time to first shortlist** | Latency and slot-filling quality | < 30 s |
| 5 | Search reached | **Search rate** | Did we understand them at all | > 70% of started |
| 6 | Car chosen | **Detail rate** | Was the shortlist any good | > 50% of searched |
| 7 | Quote produced | **Quote rate** | The moment of commercial intent | > 45% of searched |
| 8 | **Offer emailed** | **★ Offers per 1,000 sessions** | **The North Star** | see below |
| 9 | Dealer contacts | **Time to dealer contact** | Where value is destroyed today (median 11.5 h) | < 1 h |
| 10 | Sale | **Close rate** | The only number that pays | 10.2% internet-lead average |

**North Star: qualified offers per 1,000 sessions.** Not "conversations
started" — that rewards a widget people open and abandon. Not sales — too slow
and too far outside our control to steer on weekly.

### Why aggressive rollout carries no unit-economics risk

Cost per emailed offer is **invariant to the start rate**. At a 5% start rate,
1,000 sessions produce 50 conversations ($6.30) and roughly 7 offers — **$0.90
per offer**. At a 1% start rate, 10 conversations ($1.26) and 1.4 offers — still
$0.90 per offer. Adoption changes volume, not unit cost.

Against carwow's €57 per enquirer, that holds at any adoption level we could
plausibly reach. There is no "let's wait until it converts better" argument.

## Guardrails — the metrics that must not move

Adoption pushed without these becomes a worse product that more people see:

| Guardrail | Why | Alarm |
|---|---|---|
| **Abandonment mid-conversation** | The honest measure of whether it is good | > 30% |
| **Turns to first shortlist** | Interrogation is the classic voice-agent failure | > 3 |
| **Tool error rate** | Every one is a visible stumble | > 2% |
| **Declined quotes shown** | Means search leaked an ineligible car | 0 — enforced in SQL |
| **Cost per offer** | Catches an agent that has started rambling | > $2 |
| **Offers per dealer callback** | If dealers ignore them, volume is vanity | falling |

## Instrumenting it, concretely

**We are closer than it looks.** The agent already produces the whole funnel as
a side effect of working:

- Every tool call is a funnel step — `find_cars` is step 5, `show_car` is 6,
  `quote_leasing` is 7, `email_offer` is 8.
- `UserData.criteria` (see `docs/PROGRESS_TRACKER.md`) already accumulates what
  was established. **The progress strip is an adoption instrument** — slots
  filled per session is a quality-of-understanding metric, free.
- The MCP tool server sees every call from every session on every laptop. It is
  the natural collector: one place, already central, already stateless.

What is missing is small:

1. **A session id** passed with each tool call (the LiveKit room name works).
2. **An append-only event log** in the tool server — one JSONL line per call:
   session, tool, arguments, latency, error. Perhaps thirty lines.
3. **Frontend events** the backend cannot see: entry point shown, button
   clicked, mic granted or denied, tab closed. A `POST /event` on the web server.
4. **A `funnel_report` tool** that reads the log and returns the table above, so
   the funnel is queryable from the same MCP session that produces it — and from
   Claude Code during development.

That is a morning's work and it turns every demo conversation into data. It is
deliberately *not* in the current build: we are frozen before the live demo, and
nothing here changes what happens on stage.

## The experiments to run first

Ranked by expected information per unit of effort:

1. **Button copy**: "What can I get for €300 a month?" against "Talk to our
   advisor". Expect the largest single effect of anything on this page.
2. **Entry point**: on arrival against on filter-failure. Tests the intent
   hypothesis directly.
3. **Text-first against voice-first.** Not just an adoption test — it tells us
   whether we are building a voice product or a conversational one.
4. **Warm start** from existing filters against a cold open.
5. **Rate-first shortlist** against price-first. Our core product claim, and
   still formally untested with real users.

## What we would say on stage about this

Adoption of a voice agent is not won inside the conversation — it is won in the
five seconds before it starts, and four of the five barriers are upstream of the
agent entirely. So we measure **offers per thousand sessions**, not conversations
started; we let people type, because half of them cannot speak; and we open the
advisor where the filters have just failed, because that is where the intent is.

And because a conversation costs eleven cents, cost per offer is the same at 1%
adoption as at 50%. Nothing about scaling this is a gamble on the unit economics.
