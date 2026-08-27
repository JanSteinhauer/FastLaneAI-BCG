"""Stable per-laptop agent identity, shared by the worker and the web server.

The agent worker registers under this name (explicit dispatch) and the web
server mints room tokens that summon exactly this name — so several people
can run full stacks on one shared LiveKit project without grabbing each
other's chats. Both processes must derive the SAME name, so it comes from
stable machine identifiers, never from per-process randomness.
"""

from __future__ import annotations

import getpass
import hashlib
import os
import socket
import uuid


def agent_name() -> str:
    """This laptop's agent name, e.g. ``advisor-annas-mbp-3f9c2a``.

    Derived from hostname + username + MAC address, so it is identical in
    every process on this machine and unique across machines. Override with
    ``LIVEKIT_AGENT_NAME`` in ``.env`` if two machines ever collide.
    """
    if override := os.getenv("LIVEKIT_AGENT_NAME"):
        return override

    host = socket.gethostname().split(".")[0].lower()
    try:
        user = getpass.getuser()
    except (KeyError, OSError):  # no USER/USERNAME in the environment — degrade
        user = ""
    mac = uuid.getnode()
    if mac & (1 << 40):
        # Multicast bit set: uuid.getnode() couldn't find a real MAC and
        # returned a PER-PROCESS random number — using it would give the
        # worker and the web server different names. Leave it out.
        mac = 0
    digest = hashlib.sha1(f"{host}|{user}|{mac}".encode()).hexdigest()[:6]
    return f"advisor-{host}-{digest}"
