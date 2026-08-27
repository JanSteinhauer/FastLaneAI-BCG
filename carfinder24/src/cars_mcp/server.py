"""MCP server for the used-car dataset — this is where your tools live.

The server owns one shared `CarsDB` instance (a plain SQL executor over the
bundled Parquet snapshot, table `ads` — run `db.query("DESCRIBE ads")` to see
the columns) and exposes tools built on top of it. It starts with no tools:
writing them is your job — see the marker below.

The in-memory database can be extended at startup — SQL helpers registered
once in `get_db()` (e.g. via `CREATE MACRO`) are usable in every query
afterwards.

The server runs standalone, next to the voice agent and the web server:

    uv run used-car-advisor-mcp            # serves http://127.0.0.1:8990/mcp
    uv run used-car-advisor-mcp --port ... # if the default port is taken

Start it first — it loads the dataset (a few seconds) and then serves MCP
over streamable HTTP. The voice agent connects to it, and you can point
other MCP clients at the same instance, e.g. for tool development:

    claude mcp add --transport http cars http://127.0.0.1:8990/mcp
"""

from __future__ import annotations

import argparse
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP

from cars_db import CarsDB

load_dotenv()  # tool credentials, e.g. the email settings for cars_mailer/mailer.py

_REPO_ROOT = Path(__file__).resolve().parents[2]

mcp = FastMCP("Used Car Advisor")


@lru_cache(maxsize=1)
def get_db() -> CarsDB:
    """The shared CarsDB, loaded on first use."""
    return CarsDB(_REPO_ROOT / "data" / "autoscout24_de.parquet")


# ---------------------------------------------------------------------------
# Tools — this is where your work happens. Anything decorated with @mcp.tool
# becomes callable by the voice agent (and every other MCP client). A tool is
# a typed Python function; the LLM reads the docstring to decide when and how
# to call it, so write it for the model, not for humans. The shape:
#
#     @mcp.tool
#     def count_cars(make: str) -> dict:
#         """Count listings of one make. make: full name, e.g. "Volkswagen"."""
#         (row,) = get_db().query(
#             "SELECT count(*) AS n FROM ads WHERE make = $make", {"make": make}
#         )
#         return {"matches": row["n"]}
#
# Two things to keep in mind: never interpolate user values into the SQL
# string (always bind them as $params), and keep results compact — they are
# read by a voice model, not shown on screen.
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the used-car MCP tools.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8990)
    args = parser.parse_args()

    get_db()  # load the dataset up front, before accepting requests
    mcp.run(transport="http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
