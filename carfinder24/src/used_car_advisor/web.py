"""Local web frontend for dev mode: static chat page plus a LiveKit token endpoint.

Run ``uv run used-car-advisor-web`` alongside ``uv run used-car-advisor dev``
and open http://localhost:8080 to chat with the advisor in the browser.

The browser client lives in ``frontend/`` at the repo root: handwritten page in
``frontend/public/``, pre-built committed bundle in ``frontend/dist/`` — see
frontend/README.md for maintainer rebuild instructions. Participants never
need Node.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import sys
from pathlib import Path

from aiohttp import web
from dotenv import load_dotenv
from livekit import api

from used_car_advisor.identity import agent_name

load_dotenv()

# This resolves to <repo>/frontend because uv installs the project editable,
# so __file__ lives in the checkout: <repo>/src/used_car_advisor/web.py.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
PUBLIC_DIR = FRONTEND_DIR / "public"  # handwritten page (index.html, page.css)
DIST_DIR = FRONTEND_DIR / "dist"  # committed build output (app.js, app.css)
REQUIRED_ENV = ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")


def _mint_token(room: str) -> str:
    """Sign a LiveKit room token (blocking JWT/HMAC work — run off the event loop)."""
    return (
        api.AccessToken()  # reads LIVEKIT_API_KEY / LIVEKIT_API_SECRET from the env
        .with_identity(f"user-{secrets.token_hex(4)}")
        .with_name("You")
        .with_grants(api.VideoGrants(room_join=True, room=room))
        # Summon THIS laptop's agent by name — see used_car_advisor/identity.py.
        .with_room_config(
            api.RoomConfiguration(
                agents=[api.RoomAgentDispatch(agent_name=agent_name())]
            )
        )
        .to_jwt()
    )


async def index(_: web.Request) -> web.Response:
    html = await asyncio.to_thread((PUBLIC_DIR / "index.html").read_bytes)
    return web.Response(body=html, content_type="text/html")


async def token(_: web.Request) -> web.Response:
    # A fresh room per chat; its token summons this laptop's agent by name,
    # so the worker joins moments after the browser does.
    room = f"web-{secrets.token_hex(4)}"
    jwt = await asyncio.to_thread(_mint_token, room)
    return web.json_response(
        {"serverUrl": os.environ["LIVEKIT_URL"], "token": jwt, "roomName": room}
    )


def main() -> None:
    missing = [key for key in REQUIRED_ENV if not os.environ.get(key)]
    if missing:
        sys.exit(
            f"Missing {', '.join(missing)}.\n"
            "Copy .env.example to .env and paste in the values from the organisers."
        )
    if not (DIST_DIR / "app.js").is_file():
        sys.exit(
            f"Web client bundle not found at {DIST_DIR}.\n"
            "This command must run from a full checkout of the repo — the frontend/ "
            "folder ships pre-built with it (no Node needed)."
        )

    parser = argparse.ArgumentParser(
        description="Web frontend for the used-car advisor"
    )
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/token", token)
    app.router.add_static("/public", PUBLIC_DIR)
    app.router.add_static("/dist", DIST_DIR)

    print(f"\n  Open http://localhost:{args.port} in your browser.")
    print(
        "  (Make sure `uv run used-car-advisor dev` is running in another terminal.)\n"
    )
    web.run_app(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
