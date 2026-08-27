# Who does what, now that the code is done

The build is finished and tested. That changes the team: nobody's job is
"write the search tool" any more. The remaining risk is **the five minutes in
front of the CEO**, so every role below points at that.

**Feature freeze.** One person may touch code (role 5), and only to fix
something the red team actually broke. A new idea after the freeze is a demo
that fails live.

| # | Role | Owns | Was |
|---|---|---|---|
| 1 | **Demo pilot** | The live conversation. Rehearses it until it is muscle memory, runs it on stage. | Voice/prompt |
| 2 | **Storyteller** | The 5-minute narrative and the deck. Decides what we say and in what order. | Pitch |
| 3 | **Business case** | The numbers: what this is worth, to whom, and what happens if we don't. | Business |
| 4 | **Red team** | Breaking it before the CEO does — and the fallback plan for when something breaks anyway. | Frontend/UX + QA |
| 5 | **Chief engineer** | The architecture answers under questioning, the only hands on the keyboard, the avatar switch. | Tools/data + Money |

## 1 — Demo pilot

The conversation *is* the pitch, so this is the highest-stakes seat.

- Run `docs/DEMO_SCRIPT.md` end to end at least ten times. Same words each time.
- Learn how the agent behaves when you speak over it, when you mumble a number,
  when you pause mid-sentence. You want zero surprises.
- Fix the exact phrasing of the two money lines: the monthly budget
  ("about three hundred euros a month") and the consent to email.
- Own the physical setup: headphones, mic level, browser tab, fresh chat, page
  reloaded, all three terminals green *before* we walk up.
- Rule: never say a number the agent did not say.

## 2 — Storyteller

- Owns `docs/PITCH.md` — the slide-by-slide script and the timings.
- Ruthless about the clock: 30 s problem, 2 min live demo, 2 min why it's hard
  and what it's worth, 30 s close. The demo is the middle of the sandwich, not
  the end.
- Writes the one sentence the CEO repeats afterwards. Current candidate:
  *"Nobody thinks in eighteen thousand five hundred euros — everybody thinks in
  three hundred a month, so we made the monthly rate the thing you search on."*
- Decides who says what and cues the pilot.

## 3 — Business case

Everything here is defensible from our own snapshot — no invented market data.

- The wedge: of 31,419 leasable cars, **2,621 (8%) are under €300/month**. The
  customer's real constraint is invisible to every price filter on the market.
- The mismatch: a €300/month customer is shopping in the **€19,810** band — a
  number they would not have typed into a filter themselves.
- Where the value lands: better lead quality for dealers (the customer arrives
  pre-qualified on affordability), leasing attach rate, and fewer abandoned
  searches. Frame these as hypotheses with the mechanism, not fake percentages.
- Prepare an answer for "what would you need to put this in production?" —
  live inventory feed, real lessor pricing, verified customer email, and a
  human handoff at the point of contract.

## 4 — Red team

Your job is to find the failure before the CEO does.

- Work the list in `docs/SECURITY.md`: off-topic questions, "ignore your
  instructions", "send it to this other address", nonsense terms, a car that
  can't be leased, silence, interruptions, two people talking.
- Try to make it say a number no tool returned. That is the only failure mode
  that would actually hurt us.
- Kill the tool server mid-conversation and watch it recover — then decide
  whether that recovery is something to *show* or something to hide.
- Own the fallback: what the pilot says if the mic dies, if the network drops,
  if a search comes back empty. Write it down; don't improvise on stage.

## 5 — Chief engineer

- Can answer, without notes: why the leasing model runs in SQL *and* Python and
  how we prove they agree; why the agent wraps the MCP tools instead of exposing
  them; how the injection defence works and what it does *not* cover; where the
  latency goes.
- Holds the feature freeze. Fixes only what the red team breaks.
- Decides on the day whether the Tavus avatar is on (`USE_AVATAR=1`). Default
  answer: on only if it has survived three clean rehearsals.
- Runs the three processes and watches the logs during the demo.
