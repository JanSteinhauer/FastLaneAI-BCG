# Tavus replicas on this account

Every face the advisor can wear. Pulled from the Tavus API on 27 August 2026: **90 stock replicas** and **5 custom** ones. Regenerate the list any time:

```bash
curl -s -H "x-api-key: $TAVUS_API_KEY" \
  "https://tavusapi.com/v2/replicas?replica_type=system&limit=100" | jq '.data[]'
```

## Replica or persona?

A **replica** is the face and the lip-sync. A **persona** is Tavus's own
conversational brain — its LLM, its prompt, its voice.

We only ever want the replica. Our conversation is driven by OpenAI's realtime
model through LiveKit, and the Tavus side runs in echo mode: it receives our
audio and animates a face to it. That is why `TAVUS_PERSONA_ID` is empty in
`.env` and should stay that way — setting one would put a second, competing
brain in the call.

## Switching

```bash
sed -i 's|^TAVUS_REPLICA_ID=.*|TAVUS_REPLICA_ID=re6220ec0195|' .env
# then restart the agent — there is no auto-reload
```

Verify it came up without opening a browser:

```bash
uv run python scripts/probe_room.py 40
```

A healthy run shows `tavus-avatar-advisor` publishing `avatar_audio` and
`avatar_video` a few seconds after the agent joins.

**Match the voice to the face.** The persona's voice is `cedar` (warm,
masculine). A female replica needs a matching gpt-realtime voice — `marin`,
`sage`, `coral` or `shimmer` — changed in the `PERSONAS` registry in
`src/used_car_advisor/agent.py`.

## Shortlist for CarFinder24

The ones actually worth considering for a used-car advisor, all `phoenix-4`:

| Replica | ID | Looks like | Thumbnail |
|---|---|---|---|
| Steve - Professional | `rdd4c86e5e1a` | Dark suit and tie, grey at the temples — the dealership look. **Our default.** | [view](https://cdn.replica.tavus.io/39167/thumbnail.jpg) |
| Raj - Business | `re6220ec0195` | Business attire, warmer read than Steve | [view](https://cdn.replica.tavus.io/39107/thumbnail.jpg) |
| Rose - Business | `r6c7a6cb6d9b` | Business attire | [view](https://cdn.replica.tavus.io/40242/thumbnail.jpg) |
| Mary - Business | `r55e6793f10f` | Business attire | [view](https://cdn.replica.tavus.io/39187/thumbnail.jpg) |
| Anna - Professional | `rf4e9d9790f0` | Business attire | [view](https://cdn.replica.tavus.io/39895/thumbnail.jpg) |
| James - Office | `rfb0463909e3` | Polo and cardigan, garden behind — approachable, not corporate | [view](https://cdn.replica.tavus.io/43019/thumbnail.jpg) |
| Victor - Office | `re3fd4adeafd` | Grey sweatshirt in a loft — older, friendly | [view](https://cdn.replica.tavus.io/43809/thumbnail.jpg) |
| Daniel - Office | `r72f7f7f7c8b` | Late twenties, casual linen shirt | [view](https://cdn.replica.tavus.io/39974/thumbnail.jpg) |

## All stock replicas

`phoenix-4` is the newer, better-looking model — prefer it. Names repeat
because most people come in several settings (Office, Home, Casual, Studio).

### phoenix-4 (38)

| Replica | ID | Thumbnail |
|---|---|---|
| Anna - Casual | `r90bbd427f71` | [view](https://cdn.replica.tavus.io/40013/thumbnail.jpg) |
| Anna - Professional | `rf4e9d9790f0` | [view](https://cdn.replica.tavus.io/39895/thumbnail.jpg) |
| Celine - Casual | `r1a0108fbd75` | [view](https://cdn.replica.tavus.io/40463/thumbnail.jpg) |
| Celine - Studio | `r4f5b5ef55c8` | [view](https://cdn.replica.tavus.io/40460/thumbnail.jpg) |
| Charlie | `rb07f6f67b52` | — |
| Daniel - Office | `r72f7f7f7c8b` | [view](https://cdn.replica.tavus.io/39974/thumbnail.jpg) |
| Danny - Outdoor | `r9211b98614f` | [view](https://cdn.replica.tavus.io/39470/thumbnail.jpg) |
| Darius - Outdoor | `r4ba1277e4fb` | [view](https://cdn.replica.tavus.io/39472/thumbnail.jpg) |
| Dawn - Casual | `re22cfdd52e0` | [view](https://cdn.replica.tavus.io/42761/thumbnail.jpg) |
| Diego - Home | `r3a715eeff8d` | [view](https://cdn.replica.tavus.io/38477/thumbnail.jpg) |
| Gabby - Home | `r291e545fd67` | [view](https://cdn.replica.tavus.io/39418/thumbnail.jpg) |
| Gloria - Bright | `r5dc7c7d0bcb` | [view](https://cdn.replica.tavus.io/39992/thumbnail.jpg) |
| Gloria - Studio | `r9664272580d` | [view](https://cdn.replica.tavus.io/39416/thumbnail.jpg) |
| Gloria - Warm | `r3f427f43c9d` | [view](https://cdn.replica.tavus.io/40031/thumbnail.jpg) |
| Helen - Casual | `r12d3eb75ec2` | [view](https://cdn.replica.tavus.io/39033/thumbnail.jpg) |
| Helen - Home | `rbd2cdb9a3f3` | [view](https://cdn.replica.tavus.io/39035/thumbnail.jpg) |
| Ivy - Casual | `r0a8102ab353` | [view](https://cdn.replica.tavus.io/49185/thumbnail.jpg) |
| James - Office | `rfb0463909e3` | [view](https://cdn.replica.tavus.io/43019/thumbnail.jpg) |
| Julia - Casual | `raf6459c9b82` | [view](https://cdn.replica.tavus.io/39359/thumbnail.jpg) |
| Kelly - Casual | `r862e3a3c5e0` | [view](https://cdn.replica.tavus.io/49179/thumbnail.jpg) |
| Lucas - Studio | `r5f0577fc829` | [view](https://cdn.replica.tavus.io/40779/thumbnail.jpg) |
| Lucy - Home | `rfc63eab317e` | [view](https://cdn.replica.tavus.io/39103/thumbnail.jpg) |
| Lucy - Studio | `r53a461095cf` | [view](https://cdn.replica.tavus.io/39101/thumbnail.jpg) |
| Mark - Casual | `rcea962f9f9b` | [view](https://cdn.replica.tavus.io/42764/thumbnail.jpg) |
| Mary - Business | `r55e6793f10f` | [view](https://cdn.replica.tavus.io/39187/thumbnail.jpg) |
| Mary - Home | `r378d159c7b0` | [view](https://cdn.replica.tavus.io/39106/thumbnail.jpg) |
| Miranda - Home | `r3cb75621574` | [view](https://cdn.replica.tavus.io/39844/thumbnail.jpg) |
| Nathan - Bookshelf | `r987f6e6f73c` | [view](https://cdn.replica.tavus.io/42542/thumbnail.jpg) |
| Raj - Business | `re6220ec0195` | [view](https://cdn.replica.tavus.io/39107/thumbnail.jpg) |
| Raj - Doctor | `r621a6013477` | [view](https://cdn.replica.tavus.io/39476/thumbnail.jpg) |
| Raj - Home | `rf8f3aa4b33e` | [view](https://cdn.replica.tavus.io/39477/thumbnail.jpg) |
| Rose - Business | `r6c7a6cb6d9b` | [view](https://cdn.replica.tavus.io/40242/thumbnail.jpg) |
| Ruby - Office | `rcc28da86847` | [view](https://cdn.replica.tavus.io/46174/thumbnail.jpg) |
| Steve - Casual | `r2a1cea82862` | [view](https://cdn.replica.tavus.io/39166/thumbnail.jpg) |
| Steve - Professional | `rdd4c86e5e1a` | [view](https://cdn.replica.tavus.io/39167/thumbnail.jpg) |
| Victor - Casual | `r1d7cf9edbb4` | [view](https://cdn.replica.tavus.io/42555/thumbnail.jpg) |
| Victor - Office | `re3fd4adeafd` | [view](https://cdn.replica.tavus.io/43809/thumbnail.jpg) |
| Zane - Casual | `ra3a03647d46` | [view](https://cdn.replica.tavus.io/49187/thumbnail.jpg) |

### phoenix-3 (52)

| Replica | ID | Thumbnail |
|---|---|---|
| Anna | `r6ae5b6efc9d` | [view](https://cdn.replica.tavus.io/20266/thumbnail.jpg) |
| Anna - Home Office | `r8086c29d9b7` | [view](https://cdn.replica.tavus.io/20635/thumbnail.jpg) |
| Anna - Office | `r4dcf31b60e1` | [view](https://cdn.replica.tavus.io/21416/thumbnail.jpg) |
| Benjamin | `r1a4e22fa0d9` | [view](https://cdn.replica.tavus.io/20269/thumbnail.jpg) |
| Beth | `rec4a4153a78` | [view](https://cdn.replica.tavus.io/21393/thumbnail.jpg) |
| Carter | `rca8a38779a8` | [view](https://cdn.replica.tavus.io/20848/thumbnail.jpg) |
| Charlie | `rf4703150052` | [view](https://cdn.replica.tavus.io/20260/thumbnail.jpg) |
| Danny | `r62baeccd777` | [view](https://cdn.replica.tavus.io/20426/thumbnail.jpg) |
| Destiny | `r38a383b0173` | [view](https://cdn.replica.tavus.io/20328/thumbnail.jpg) |
| Diego - Office V2 | `r044d76f4490` | [view](https://cdn.replica.tavus.io/20340/thumbnail.jpg) |
| Gabby | `rdf61be0d4e1` | [view](https://cdn.replica.tavus.io/35451/thumbnail.jpg) |
| Gloria | `r4317e64d25a` | [view](https://cdn.replica.tavus.io/20264/thumbnail.jpg) |
| Gloria - Conversational | `rbe2c395e725` | [view](https://cdn.replica.tavus.io/20357/thumbnail.jpg) |
| Gloria - Greenscreen | `rb67667672ad` | [view](https://cdn.replica.tavus.io/21831/thumbnail.jpg) |
| Gloria - Vertical | `rb54819da0d5` | [view](https://cdn.replica.tavus.io/20367/thumbnail.jpg) |
| Ivy | `r991fc9af2be` | [view](https://cdn.replica.tavus.io/35249/thumbnail.jpg) |
| Jackie - Office | `r67d1c9cac37` | [view](https://cdn.replica.tavus.io/20275/thumbnail.jpg) |
| Jackie - Office V1 | `r754557e5758` | [view](https://cdn.replica.tavus.io/20294/thumbnail.jpg) |
| Jakey | `r5fb46c843a8` | [view](https://cdn.replica.tavus.io/31784/thumbnail.jpg) |
| James | `r92debe21318` | [view](https://cdn.replica.tavus.io/20430/thumbnail.jpg) |
| James - Home Office | `r873e4707689` | [view](https://cdn.replica.tavus.io/34708/thumbnail.jpg) |
| Julia | `rdc96ac37313` | [view](https://cdn.replica.tavus.io/21556/thumbnail.jpg) |
| Julia - Home Office | `rb43357fb2ee` | [view](https://cdn.replica.tavus.io/35453/thumbnail.jpg) |
| Kai | `r31e11adf1d3` | [view](https://cdn.replica.tavus.io/31785/thumbnail.jpg) |
| Katya | `r6fb41bf13b4` | [view](https://cdn.replica.tavus.io/35449/thumbnail.jpg) |
| Katya 2 | `r5791c5ab229` | [view](https://cdn.replica.tavus.io/35447/thumbnail.jpg) |
| Liam | `r90a0339d496` | [view](https://cdn.replica.tavus.io/31783/thumbnail.jpg) |
| Liam 2 | `r158ac53345d` | [view](https://cdn.replica.tavus.io/31779/thumbnail.jpg) |
| Liam 3 | `rc2f861e78a7` | [view](https://cdn.replica.tavus.io/31782/thumbnail.jpg) |
| Luna | `r9d30b0e55ac` | [view](https://cdn.replica.tavus.io/20258/thumbnail.jpg) |
| Luna - Home  | `r1e52660d3bf` | [view](https://cdn.replica.tavus.io/35455/thumbnail.jpg) |
| Luna - Home 2 | `re5c4a8dd5ea` | [view](https://cdn.replica.tavus.io/35457/thumbnail.jpg) |
| Mary | `r6ca16dbe104` | [view](https://cdn.replica.tavus.io/20941/thumbnail.jpg) |
| Mary - Office | `r68fe8906e53` | [view](https://cdn.replica.tavus.io/20272/thumbnail.jpg) |
| Nathan - Bookshelf | `rfe12d8b9597` | [view](https://cdn.replica.tavus.io/21548/thumbnail.jpg) |
| Olivia | `rc2146c13e81` | [view](https://cdn.replica.tavus.io/20262/thumbnail.jpg) |
| Olivia - Doctor | `rd3ba0f30551` | [view](https://cdn.replica.tavus.io/20310/thumbnail.jpg) |
| Olivia - Office | `r9fa0878977a` | [view](https://cdn.replica.tavus.io/20283/thumbnail.jpg) |
| Owen   | `r9458111c64a` | [view](https://cdn.replica.tavus.io/34825/thumbnail.jpg) |
| Owen - Home Office | `r2a31940a5f0` | [view](https://cdn.replica.tavus.io/34766/thumbnail.jpg) |
| Raj | `ra066ab28864` | [view](https://cdn.replica.tavus.io/20280/thumbnail.jpg) |
| Raj - Doctor | `r18e9aebdc33` | [view](https://cdn.replica.tavus.io/20313/thumbnail.jpg) |
| Rose | `r1af76e94d00` | [view](https://cdn.replica.tavus.io/20305/thumbnail.jpg) |
| Rose - Home Office | `r3f8decedbd2` | [view](https://cdn.replica.tavus.io/34861/thumbnail.jpg) |
| Ruby | `re3a705cf66a` | [view](https://cdn.replica.tavus.io/32800/thumbnail.jpg) |
| Ruby 2 | `ree20a3c764c` | [view](https://cdn.replica.tavus.io/31805/thumbnail.jpg) |
| Samantha - Office V1 | `rf6b1c8d5e9d` | [view](https://cdn.replica.tavus.io/34696/thumbnail.jpg) |
| Samantha - Office V2 | `r38e4c3bc562` | [view](https://cdn.replica.tavus.io/20337/thumbnail.jpg) |
| Santa | `raa1d440ec4a` | [view](https://cdn.replica.tavus.io/20366/thumbnail.jpg) |
| Steph - Office V1 | `r9c55f9312fb` | [view](https://cdn.replica.tavus.io/20267/thumbnail.jpg) |
| Steph - Office V2 | `r6c4e43b78b1` | [view](https://cdn.replica.tavus.io/20334/thumbnail.jpg) |
| Zane | `r24efb3b9bef` | [view](https://cdn.replica.tavus.io/35227/thumbnail.jpg) |

## Custom replicas on this account

Not stock — these were trained by whoever owns the Tavus account, and three of
them are of **Manuel Diehn**, one of the BCG organisers. They are real people's
likenesses. Do not put one on stage without asking that person first; a face
used without consent is a much bigger problem than a boring avatar.

| Replica | ID | Status |
|---|---|---|
| Manuel Diehn September 17 2025 | `r67aec1a01c2` | completed |
| 9/30/25 | `r8822388dcc7` | completed |
| Manuel Diehn October 04 2025 | `rb2594600560` | completed |
| Manuel Diehn February 17 2026 | `r658d179c8a7` | error |
| Manuel Diehn February 17 2026 | `rd009fc06244` | completed |

## Personas (28)

Listed for completeness only — see *Replica or persona?* above. We use none of
them.

| Persona | ID | Pipeline |
|---|---|---|
| ? | `p4c39b1d500d` | full |
| AI Interviewer | `pe13ed370726` | full |
| AI Trivia Host | `p89b602b1174` | full |
| Ari | `pipecat0` | echo |
| Casting Director Julian | `p735435f8c36` | full |
| Charlie | `p0f105b5b82e` | full |
| Charlie — PAL Maker Fanout v2 reduced prompt | `p1abc173c043` | full |
| Chatty Cathy | `pc1fdada4034` | full |
| Customer Support | `paaee96e4f87` | full |
| Gigi - Banter Buddy | `p82d609f1748` | full |
| Healthcare Intake Assistant | `p5d11710002a` | full |
| Healthcare Intake Assistant | `pa5ad6596ef5` | full |
| History Teacher | `pc55154f229a` | full |
| Interviewer | `pdac61133ac5` | full |
| Livekit Tavus Persona | `pb87e71797da` | echo |
| Meeting Avatar | `paf0c2da1c78` | full |
| Mentor | `pfb078329b77` | full |
| My Persona | `p4cdc13e6a32` | echo |
| Nathan Roleplay Coach | `pa9c7a69d551` | full |
| Personal Assistant Hudson | `p72bafe6bb9a` | full |
| Sales Coach | `pdced222244b` | full |
| Sales Coach | `p1af207b8189` | full |
| Sales Development Rep | `pcb7a34da5fe` | full |
| Santa | `p3bb4745d4f9` | full |
| Sara - Friendly Tutor | `p1b06420cfdc` | full |
| Tavus Echo Audio Stream | `pipecat-stream` | echo |
| Tavus Researcher | `p48fdf065d6b` | full |
| Tavus' Personal AI | `p2fbd605` | full |
