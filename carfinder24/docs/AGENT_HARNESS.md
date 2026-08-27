# The agent harness

How the agent is put together, and how to change it without breaking the demo.

## Anatomy

```
src/used_car_advisor/
  agent.py       personas, the realtime model, the avatar, the entrypoint
  prompts.py     the advisor's instructions
  tools.py       the five voice-facing tools (thin wrappers over MCP)
  mcp_client.py  one persistent MCP session, with reconnect
  ui.py          what gets drawn on the web page
  state.py       session plumbing (room, personas, tool client)
  identity.py    this laptop's agent name — do not touch
src/cars_mcp/
  server.py      the tools themselves
  guards.py      input/output sanitising
```

A **persona** is a prompt + a voice + a colour + a set of tools. One is
registered (`advisor`), on purpose: the journey — search, advise, quote, email
— is one continuous conversation, and every handover costs a turn of latency
and a chance to lose the thread. The registry stays because it is the harness;
`switch_persona` is only attached to personas that actually have `transfers`,
so the model never sees a tool it cannot use.

## Adding a tool

1. Write it in `src/cars_mcp/server.py` with `@mcp.tool`. Bind every caller
   value as a `$param`. Keep the result small — it is spoken aloud.
2. Write the docstring **for the model**: when to reach for it, what the
   arguments mean, what to do with the answer. That text is the only
   instruction the model gets at call time.
3. Add a wrapper in `src/used_car_advisor/tools.py` (call, draw, return) and
   list it in `ADVISOR_TOOLS`.
4. Restart the tool server, then the agent. Start a fresh chat.

If you want the model to reach a tool *unmediated* instead, put its name in the
persona's `mcp_tools` — the `MCPToolset` path from the handover code is still
wired in `PersonaAgent.__init__`. You lose the screen and the argument repair.

## Adding a persona

Add an entry to `PERSONAS`, add its name to the `PersonaName` literal, and list
it in the `transfers` of whoever may reach it. The full chat context is carried
across, so the new persona infers everything from the conversation.

## Rules that cost someone an hour

- **No auto-reload.** Changed tools → restart the tool server. Changed prompt or
  persona → restart the agent. Then start a *new* chat.
- **Tool server first**, always: the agent connects at startup.
- A tool not listed in `ADVISOR_TOOLS` (or in `mcp_tools`) does not exist as far
  as the model is concerned.
- Port taken? `--port` on the web and tool servers; if the *tool* server moves,
  update `MCP_URL` in `.env` and restart the agent.
- When things get weird: restart 1 → 2 → 3, reload the page, fresh chat.

## Failure behaviour

| Failure | What the customer experiences |
|---|---|
| Tool server down | "The listings service is not reachable" — one turn lost, session survives; reconnects on the next call |
| Tool rejects the call (bad ref, unknown body type) | The model gets the reason and corrects itself in the same turn |
| Terms out of range | Snapped to the nearest allowed tier before the call; if still impossible, a spoken reason and an alternative |
| Car cannot be leased | Never happens for a searched car — search filters on the same rules |
| Tavus avatar fails | Logged; the session continues audio-only |
| Email misconfigured / rejected | "I could not send it" — never a silent success |

## The avatar (cherry on top)

Off by default. `USE_AVATAR=1` in `.env` starts a Tavus replica that lip-syncs
the advisor's voice; the frontend already renders any participant whose identity
is `tavus-avatar-<persona>`. With the avatar on, the agent stops publishing its
own audio (`RoomOutputOptions(audio_enabled=False)`) — the avatar worker
publishes the lip-synced track, and publishing both would double the voice.
Override the replica with `TAVUS_REPLICA_ID`; the default is the stock replica
"Charlie". A failure *at startup* can never take the voice down: it is caught,
logged, and the session continues without a face.

**Verified**: with `USE_AVATAR=1` the Tavus participant joins as
`tavus-avatar-advisor` and publishes `avatar_audio` + `avatar_video` about three
seconds after the agent — which is exactly what `frontend/src/main.jsx` looks
for. Check it yourself without a browser, a mic or a camera:

```bash
uv run python scripts/probe_room.py 50
```

It dispatches the worker the way the web page does and prints who joined and
what they published. Use it to confirm the stack is alive before rehearsals.

**The trade-off to decide before the demo**: with the avatar on, the *avatar*
publishes the voice. A Tavus outage at startup degrades gracefully, but one
mid-session takes the audio with it. Audio-only is the safer demo; the face is
the better story. `USE_AVATAR` is the switch, and the agent must be restarted
after flipping it.
