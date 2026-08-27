"""Join a LiveKit room headlessly and report who else shows up.

Exercises the agent's entrypoint without a browser, a microphone or a human: it
dispatches the worker exactly the way web.py does, then watches who joins and
what they publish. The fastest way to answer "is the agent actually alive, and
did the avatar come up?" — and the only way to check the avatar on a machine
with no camera.

    uv run python scripts/probe_room.py [seconds]

A healthy run with USE_AVATAR=1 prints the agent participant (state
`listening`, attributes `agent` / `agent_color`) plus `tavus-avatar-advisor`
publishing `avatar_audio` and `avatar_video`. With the avatar off, the agent
publishes its own audio track instead.
"""
import asyncio, os, secrets, sys
from pathlib import Path
from dotenv import load_dotenv
from livekit import api, rtc
from used_car_advisor.identity import agent_name

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

async def main() -> None:
    room_name = f"probe-{secrets.token_hex(3)}"
    token = (
        api.AccessToken()
        .with_identity("probe-user")
        .with_name("Probe")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .with_room_config(
            api.RoomConfiguration(agents=[api.RoomAgentDispatch(agent_name=agent_name())])
        )
        .to_jwt()
    )
    room = rtc.Room()

    @room.on("participant_connected")
    def _p(p: rtc.RemoteParticipant) -> None:
        print(f"  + participant joined: {p.identity!r}", flush=True)

    @room.on("track_published")
    def _t(pub, p) -> None:
        print(f"  + track published by {p.identity!r}: {pub.kind} {pub.name!r}", flush=True)

    await room.connect(os.environ["LIVEKIT_URL"], token)
    print(f"joined room {room_name}", flush=True)
    await asyncio.sleep(int(sys.argv[1]) if len(sys.argv) > 1 else 45)

    print("\n--- final state ---")
    for p in room.remote_participants.values():
        tracks = [f"{t.kind}:{t.name}" for t in p.track_publications.values()]
        print(f"  {p.identity!r}  attrs={dict(p.attributes)}  tracks={tracks}")
    if not room.remote_participants:
        print("  (nobody joined)")
    await room.disconnect()

asyncio.run(main())
