# FastLaneAI-BCG

BCG X Entry Event Berlin — team **Fast Lane AI**.

CarFinder24 voice advisor: a voice agent that searches ~46k German used-car
listings, quotes a leasing rate, and emails the offer.

- `CarFinder24-Kickoff.md` — case scope, repo state, team plan, chosen approach.
- `carfinder24/` — the project. See its README to get running (`uv sync`, then
  the three processes: MCP tool server → agent → web).

Copy `carfinder24/.env.example` to `carfinder24/.env` and fill in the team
credentials. `.env` and `.claude/settings.json` are gitignored — never commit keys. For
Claude Code, create `carfinder24/.claude/settings.json` with
`{"env": {"ANTHROPIC_API_KEY": "<team key>"}}`.



https://tumde-my.sharepoint.com/:p:/g/personal/louis_forster_tum_de/IQBr7QnveYI-RZNYzINlelbMAXiYcbFoxcfF9xLivpCFtGo?e=I7GEuW
