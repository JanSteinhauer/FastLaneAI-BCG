# What one conversation costs

Run it yourself: `uv run python scripts/cost_model.py`. Every rate is a named
constant at the top of that file; sources at the bottom of this page.

## The answer

| | Voice only | With the Tavus avatar |
|---|---:|---:|
| Short — 3 questions | $0.054 | $0.610 |
| **Median — 6 questions** | **$0.126** | **$1.238** |
| Long — 10 questions | $0.252 | $2.477 |
| Per 1,000 median conversations | **$126** | **$1,238** |

The median interaction — six exchanges, 36 seconds of customer speech, 60
seconds of agent speech, a three-minute session, one emailed offer — costs
**about twelve cents.** Roughly €0.11.

## The formula

```
Cost  =  0.00032 · Sc          seconds the customer speaks
      +  0.00128 · Sa          seconds the agent speaks
      +  0.0105  · M           minutes the room is open
      +  0.37    · max(0.5, M) · avatar
      +  0.0001  · E           emails sent
```

`Sc`, `Sa` in seconds; `M` in wall-clock minutes; `avatar` is 1 or 0; `E` is
emails. The two speech coefficients come straight from the token rates:

- the Realtime API bills **600 tokens per minute of customer speech** and
  **1,200 per minute of agent speech** — 10 and 20 tokens a second;
- at $32 / 1M in and $64 / 1M out, that is **$0.00032 per second the customer
  talks** and **$0.00128 per second the agent talks**.

**A second of agent speech costs four times a second of customer speech.**
Two of those factors compound: the agent produces twice the tokens per second
*and* pays twice per token.

Dropped from the formula because they round to nothing at this scale: the
cached conversation history ($0.0016 of the median), the system prompt and tool
schemas ($0.0041), LiveKit bandwidth ($0.0001 audio-only), and SES ($0.0001).

## Where the money actually goes

Median voice-only conversation, $0.1257:

| Component | Cost | Share |
|---|---:|---:|
| OpenAI — agent speech | $0.0768 | 61% |
| OpenAI — customer speech | $0.0115 | 9% |
| OpenAI — prompt, tools, cached history | $0.0057 | 5% |
| LiveKit — agent session minutes | $0.0300 | 24% |
| LiveKit — participant + bandwidth | $0.0016 | 1% |
| AWS SES — the offer email | $0.0001 | 0.1% |

**The dominant cost is how much the agent talks.** Which means the prompt rule
*"two sentences is a good answer; five is too many"* is not only a UX decision —
it is the single biggest lever on unit cost. An agent that answered in 20-second
paragraphs instead of 10 would cost **$0.203 per conversation, 61% more**, for a
worse conversation.

The thing people expect to hurt — the Realtime API re-sending the entire
conversation on every turn, which is quadratic in turns — costs **$0.0016**,
because cached audio input is $0.40/1M against $32/1M fresh. It is 1.3% of the
bill. Caching is what makes long conversations affordable; without it the median
would be roughly $0.22 and the long case would be far worse.

## The avatar is not a rounding error

Tavus at $0.37/minute makes the median conversation **ten times more
expensive**: $1.24 against $0.126. It is 90% of the bill, and it is billed on
*wall-clock* minutes — thinking time, reading time, silence — not on speech, so
it is the one component that gets worse when a customer pauses to consider.

That is fine for a demo in front of a CEO, where the face is the point. It is a
product decision at scale: the avatar has to be worth more than nine additional
conversations, because that is what it costs.

## Levers, in order of size

1. **Turn the avatar off** outside the demo: −90%.
2. **Keep the agent terse.** Every 10 seconds shaved off the average answer is
   about −$0.013 per conversation.
3. **`gpt-realtime-2.1-mini`** at $10/$20 per 1M instead of $32/$64 would take
   the median to roughly **$0.065**, about half. Worth testing whether the
   smaller model still handles the tool-calling reliably.
4. **Close the room when the conversation ends.** LiveKit agent-session minutes
   are 24% of the voice-only cost and they run on wall-clock time; a session
   left open after the customer stops talking bills for nothing.
5. Prompt and tool schemas are 1,711 tokens re-sent every turn — real, but
   worth $0.004. Do not trade clarity in a tool docstring for that.

## What it means commercially

Every conversation that ends in an emailed offer is a lead, delivered for
**about eleven cents**, with the customer's budget, mileage, term and chosen car
attached — a far better qualified lead than a form fill.

The comparison to make on stage is against what a dealer currently pays for a
used-car lead. We deliberately do not put a number on that here: it is the one
figure in this document we cannot compute from our own data, and inventing it
would undermine everything we can.

At 1,000 conversations a day, voice-only, the stack costs **$126/day** —
roughly $46,000 a year — plus LiveKit and Tavus plan floors. That is the number
to hold against the value of a thousand qualified leads a day.

## Assumptions

The median conversation is modelled as six exchanges, six seconds of customer
speech and ten of agent speech each, a three-minute session, one email. Those
speech figures match the demo script; the session length assumes the customer
spends about half the call listening, reading the screen and thinking.

The model ignores plan floors — LiveKit Ship at $50/month, Tavus Starter at
$22–59/month — because they are fixed costs, not per-interaction ones. Below a
few thousand conversations a month the plan fee, not the usage, is your bill.

## Sources

Rates are list prices as of August 2026:

- OpenAI `gpt-realtime-2.1`: $32 / 1M audio input, $64 / 1M audio output,
  $0.40 / 1M cached input; 600 and 1,200 tokens per minute of speech
- LiveKit Cloud: $0.01 per agent-session minute, $0.0005 per WebRTC participant
  minute, $0.10–0.12 per GB downstream, upstream free
- Tavus CVI: $0.37 per minute, 30-second minimum per conversation
- Amazon SES: $0.10 per 1,000 emails

The 1,711-token fixed context is measured from `prompts.py` and the five tool
docstrings, not estimated.
