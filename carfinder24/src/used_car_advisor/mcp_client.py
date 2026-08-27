"""Persistent client for the MCP tool server.

The agent could hand the raw MCP toolset to the model (`mcp.MCPToolset`, still
supported by the harness — see docs/AGENT_HARNESS.md). It deliberately does not:
a thin wrapper around each call is what lets the agent *draw the answer on the
web page* while it speaks, keep what goes back into the model small, and turn a
tool error into a sentence the advisor can say instead of a dropped turn.

Latency matters in a voice call, so the MCP session is opened once and reused;
a dead session is transparently reconnected on the next call.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp import Client
from fastmcp.exceptions import ToolError as MCPToolError

logger = logging.getLogger("used-car-advisor.tools")

CALL_TIMEOUT_S = 20.0


class ToolError(RuntimeError):
    """A tool call failed in a way worth telling the customer about."""


def _message(exc: Exception) -> str:
    """The useful half of an MCP error string."""
    text = str(exc).strip()
    marker = "': "  # "Error calling tool 'search_cars': unknown body_type ..."
    if text.startswith("Error calling tool") and marker in text:
        text = text.split(marker, 1)[1]
    return text or "the tool call failed"


class ToolClient:
    """One long-lived MCP session, with reconnect."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: Client | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Open the session up front, so the first customer question is not slow."""
        await self._ensure()

    async def _ensure(self) -> Client:
        async with self._lock:
            if self._client is not None and self._client.is_connected():
                return self._client
            client = Client(self._url)
            await client.__aenter__()
            self._client = client
            logger.info("connected to MCP tool server at %s", self._url)
            return client

    async def _drop(self) -> None:
        async with self._lock:
            client, self._client = self._client, None
        if client is not None:
            try:
                await client.__aexit__(None, None, None)
            except Exception:
                logger.debug("closing stale MCP session failed", exc_info=True)

    async def call(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool, reconnecting once if the session went stale.

        Tool-level errors (a bad ref, an unknown body type) come back as a
        `ToolError` carrying the server's message — the model reads it and can
        correct itself in the same turn.
        """
        args = {k: v for k, v in arguments.items() if v is not None}
        last: Exception | None = None
        for attempt in (1, 2):
            try:
                client = await self._ensure()
                result = await client.call_tool(name, args, timeout=CALL_TIMEOUT_S)
                if result.is_error:
                    text = "; ".join(
                        getattr(c, "text", "") for c in (result.content or [])
                    ).strip()
                    raise ToolError(text or f"{name} failed")
                return result.data
            except MCPToolError as exc:
                # The tool itself rejected the call (bad ref, unknown body type).
                # That is an answer, not an outage: hand the message to the model
                # so it can correct itself in the same turn — retrying is useless.
                raise ToolError(_message(exc)) from exc
            except ToolError:
                raise
            except Exception as exc:  # transport-level: retry once on a fresh session
                last = exc
                logger.warning("MCP call %s failed (attempt %d): %s", name, attempt, exc)
                await self._drop()
        raise ToolError(
            f"The {name} service is not reachable — is the MCP tool server running?"
        ) from last

    async def aclose(self) -> None:
        await self._drop()
