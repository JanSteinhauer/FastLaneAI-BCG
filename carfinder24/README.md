# Handover: the CarFinder24 voice advisor

Hi — welcome to the project! I've been building the voice advisor for
CarFinder24, a used-car advisory for the German market, and today I'm
handing it over to you.

Here's where things stand: the plumbing works. Visitors open a web page,
click "Start chat", and talk to the agent — voice in, voice out, no typing.
A snapshot of ~46,000 real German used-car listings (AutoScout24, November
2025) is loaded and queryable. The front desk greets visitors warmly and
asks what they're looking for.

And then... nothing. It can't search cars, can't advise, can't do anything
yet — I only got the foundation done. Making it actually useful is yours
now. What I can give you is a quick start and the notes I wish someone had
given me.

## What it does now — team Fast Lane AI

The advisor is built. A visitor talks to it, and it:

1. leads them from vague to specific — and when they say "I don't know", asks
   what the car is *for* and works the answer out from that, with reasons;
2. asks what they want to spend **per month** and searches 45,611 real listings
   by *monthly leasing rate* — not by sticker price (or by purchase price, if
   they would rather buy);
3. shows the shortlist on their screen while it talks, partner dealers first
   and badged as such;
4. looks a car up in detail and scores whether it is a good price, out of five,
   against comparable listings;
5. quotes the exact, bindable leasing rate — and explains, step by step, where
   that number came from;
6. refuses terms we do not offer instead of quietly rounding them, and says
   which ones we do;
7. summarises what they chose and why that car answers it;
8. emails the offer, with the draft leasing agreement attached as a PDF if they
   ask for the contract itself.

Read `docs/` before changing anything:

| Doc | What's in it |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | The advisory funnel, the three processes, the ten tools, and the five design decisions worth defending |
| [docs/AGENT_HARNESS.md](docs/AGENT_HARNESS.md) | How to add a tool or a persona, the restart rules, failure behaviour, the Tavus avatar |
| [docs/SECURITY.md](docs/SECURITY.md) | Threat model: conversation injection, injection through listing data, outbound abuse, false statements |
| [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | The rehearsed live demo, line by line |
| [docs/PITCH.md](docs/PITCH.md) | The five-minute pitch: beats, timings, the words |
| [docs/ROLES.md](docs/ROLES.md) | Who does what now that the code is frozen |
| [docs/pitch-deck.html](docs/pitch-deck.html) | The deck itself — arrow keys, `N` for speaker notes, `T` for the rehearsal timer |

`uv run pytest tests -q` — 128 tests. The ones worth knowing about: the parity
check that stops the SQL and Python leasing models from ever disagreeing, the
refusal tests that stop a customer being rounded onto terms they never chose,
and the deal-score tests that keep "is this a good price?" arithmetic. Nothing
in the suite sends an email — the mailer is replaced with a recorder.

Two switches in `.env`: `USE_AVATAR=1` gives the advisor a Tavus face,
`DEMO_INJECTION=1` plants the hostile listing used in the security demo.

---

## Getting it running (~10 minutes)

Grab the project folder. Then, in a terminal inside the folder: `uv sync`.

Copy `.env.example` to `.env` and fill in the values from the API Keys Word file
on the same SharePoint.

Claude Code is set up the same way: paste your team's Claude key from the
same Word file into `.claude/settings.json` (replace the placeholder), then
run `claude` *inside the project folder* — it asks once whether to use that
key; say yes. A good first move is `/init` — it explores the repo and
writes itself a `CLAUDE.md` cheat sheet, so every later prompt starts
oriented. It was my pair programmer on this; make it yours.

The stack is three processes, three terminals, in this order:

```bash
uv run used-car-advisor-mcp   # 1 — data & tool server (loads the dataset, start it first)
uv run used-car-advisor dev   # 2 — the voice agent (ignore the deprecation warning)
uv run used-car-advisor-web   # 3 — the web page
```

Using VS Code? One keystroke does all of that: press `Ctrl+Shift+B`
(`Cmd+Shift+B` on Mac) and a prepared task starts the three processes in
the right order, each in its own terminal split. Restarting one after a
code change: click into its split, `Ctrl-C`, then *Terminal → Run Task* and
pick just that one.

Open http://localhost:8080, start a chat, unmute the mic (allow access when
the browser asks), say hi. Wear headphones — on open speakers the agent
hears itself and gets confused.

One orientation note and you're off: everything you'll ever need to change
lives in `src/` — the agent, its prompts, and its tools are all in there,
and it's small enough to read over one coffee. The frontend is working right now
as it is. Feel free to change or improve it if you want to.

## What the `.env` values are for

- `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` — the voice
  transport. LiveKit hosts the room where your browser and the agent meet;
  both the web page and the agent use these.
- `OPENAI_API_KEY` — the brain and the voice in one: OpenAI's realtime
  model does the listening, thinking, and speaking as a single stream.
- `MCP_URL` — where the agent finds your tool server. The default matches
  terminal 1; only touch it if you move the port.
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` /
  `EMAIL_RECIPIENT` — lets the project send real emails
  (`src/cars_mailer/` is ready-made for it); `EMAIL_RECIPIENT` is the
  fixed address everything goes to.
- `TAVUS_API_KEY` — from an experiment I never got to finish. I left the
  key in, in case one of you feels adventurous. See more here:
  https://docs.livekit.io/agents/models/avatar/plugins/tavus/

## Notes I wish someone had given me

- **There's no auto-reload.** Changed Python? `Ctrl-C` the affected process
  and start it again — the tool server after tool changes, the agent after
  persona/prompt changes. Then start a *new* chat.
- **A new tool won't show up by itself.** After writing it in `server.py`,
  list its name in the persona's `mcp_tools` in `agent.py` — each persona
  only sees the tools it's given. (This one cost me an hour.)
- Start the tool server before the agent, or the agent comes up without
  tools and stays that way until you restart it.
- Port already taken? The web page and the tool server both accept
  `--port` (e.g. `uv run used-car-advisor-web --port 8081`). If you move
  the *tool server*, update `MCP_URL` in `.env` to match and restart the
  agent.
- When things get weird: restart all three terminals (1 → 2 → 3), reload
  the page, fresh chat. Fixes ninety percent of it. For the rest, wave one
  of us over — we're in the room.

One last thing: you're showing this live at the end — the conversation with
your agent *is* the pitch. From someone who has demoed voice agents: a
short, rehearsed, flawless conversation beats a long ambitious one every
time.

Have fun with it. Build something you'd want to talk to.
