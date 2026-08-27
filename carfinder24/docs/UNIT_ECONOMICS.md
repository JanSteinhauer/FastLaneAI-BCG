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

## What the market pays for the same thing

Our eleven cents only means something against what a lead actually costs today.
These are published 2026 benchmarks; sources at the bottom.

### Per lead

| What | Cost per lead |
|---|---|
| **carwow** — per enquirer passed to a dealer | **£49 + VAT** (≈ €57) |
| Pay-per-lead providers (Autotrader, Cars.com and similar) | $40–100 |
| Google Vehicle Ads, well optimised | $25–45 |
| Reported dealership average | $42.95 |
| Cox Automotive 2026 industry average (all-in spend ÷ leads) | **$326** — up 15.2% on 2025; EV leads $412 |
| **CarFinder24 advisor, per emailed offer** | **$0.126** |

carwow is the comparison that matters: same product shape — an online car-buying
platform that hands qualified enquiries to dealers — in the same markets, the UK
and Germany. They charge **£49 per enquirer**, plus a success fee of **£250–500
per sale**. We produce a *more* qualified enquiry — budget, mileage, term, down
payment and a specific car, all confirmed out loud — for about **1/500th** of
what they charge for one.

### Per sale

| What | Cost per sale |
|---|---|
| carwow success fee | £250–500 |
| Industry cost per vehicle sold | $250–350 |
| NADA, all channels, per new vehicle | $739 |
| Third-party-sourced sales | $800–1,000 |
| Owned-channel sales | $100–200 |
| **Ours at a 10.2% close rate** | **$1.23** |
| **Ours at a pessimistic 2.5% close rate** | **$5.04** |

Internet leads close at about **10.2%** on average, third-party leads at 8–12%,
and a dealer's own-website leads at **15–25%** — four to five times better,
because they are exclusive and the visitor came on purpose.

### What German dealers actually pay the portals

- **mobile.de**: roughly €30 per listing plus a €60 monthly base; high-volume
  dealers get under €10 per vehicle.
- **AutoScout24**: moved to a performance-based tariff in 2026, a **25–30%
  increase** for many dealers.
- A mid-sized dealership pays **€1,500–3,000 a month** to the portals —
  €18,000–36,000 a year — for leads it does not own.

That last phrase is the opening. Dealers are paying more every year for leads
that are rented, not owned, and portal pricing is going up, not down.

## The honest version of this comparison

**Our $0.126 is marginal inference cost, not customer acquisition cost.** It
does not include getting the visitor to the page — and for a dealer, that *is*
the cost. A €326 cost per lead mostly buys attention: persuading a stranger to
raise their hand. We do not buy attention. We convert attention the platform
already has.

It also excludes engineering, inventory data, support, compliance, and the
LiveKit and Tavus plan floors. Anyone who claims "500× cheaper than carwow" from
this page is claiming something the page does not support, and a partner will
take it apart in one question.

The defensible claim is narrower and better:

> Owned-channel leads convert at 15–25% against 8–12% for bought ones, and cost
> $100–200 per sale against $800–1,000. Our advisor is an owned-channel tool
> that makes the best-converting category better — and its running cost rounds
> to zero against either number.

### The payback, which is the number to say out loud

An additional used-car sale carries **$1,253–3,000** of front-end gross.

At $0.126 per conversation, that one extra sale pays for **roughly 10,000 to
24,000 conversations**.

So the advisor pays for itself if it produces **one additional sale per ~10,000
conversations** — a lift of about **0.01%**. Every conversation after that is
margin. That is the whole business case, and it does not depend on any number we
had to invent.

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

Market benchmarks: carwow's published dealer price list (£49 + VAT per
enquirer, £250–500 success fee); Cox Automotive 2026 Dealer Digital Marketing
Report ($326 average CPL, +15.2% year on year); NADA ($739 per new vehicle
across all channels); 2026 automotive marketing benchmark round-ups for close
rates (10.2% internet leads, 15–25% own-site) and cost per sale; German portal
pricing from kfz-betrieb and dealer-press reporting on the 2026 AutoScout24
tariff change; used-vehicle front-end gross of $1,253 (Q1 2026 average) to
$2,000–3,000 (healthy).

The 1,711-token fixed context is measured from `prompts.py` and the five tool
docstrings, not estimated.
