"""In-process WebSocket fan-out for live updates.

Design notes
------------
Domain code never imports WebSocket types: services call :func:`publish` with a
plain event dict, and the manager delivers it to whoever is connected. That keeps
realtime an *additive* concern — if nothing is connected, publishing is a no-op,
and the REST API remains the source of truth.

The frontend treats events purely as cache-invalidation hints (it refetches the
affected queries) rather than trusting the payload, so a dropped or duplicated
event can never corrupt what a user sees.

Scope: a single process. With multiple backend replicas this would need a shared
broker (Redis pub/sub); see docs/architecture.md.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger("realtime")


class ConnectionManager:
    def __init__(self) -> None:
        # user_id -> set of sockets (a user may have several tabs open)
        self._connections: dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(user_id, set()).add(ws)
        logger.info("ws connected user=%s (total=%s)", user_id, self.count())

    async def disconnect(self, user_id: int, ws: WebSocket) -> None:
        async with self._lock:
            sockets = self._connections.get(user_id)
            if sockets:
                sockets.discard(ws)
                if not sockets:
                    self._connections.pop(user_id, None)

    def count(self) -> int:
        return sum(len(s) for s in self._connections.values())

    async def broadcast(self, event: dict[str, Any], *, exclude_user: int | None = None) -> None:
        """Send an event to every connected client (optionally skipping the actor,
        whose own UI already updated optimistically)."""
        if not self._connections:
            return
        dead: list[tuple[int, WebSocket]] = []
        for user_id, sockets in list(self._connections.items()):
            if exclude_user is not None and user_id == exclude_user:
                continue
            for ws in list(sockets):
                try:
                    await ws.send_json(event)
                except Exception:
                    dead.append((user_id, ws))
        for user_id, ws in dead:
            await self.disconnect(user_id, ws)

    async def send_to_user(self, user_id: int, event: dict[str, Any]) -> None:
        for ws in list(self._connections.get(user_id, ())):
            try:
                await ws.send_json(event)
            except Exception:
                await self.disconnect(user_id, ws)


manager = ConnectionManager()


def publish(event_type: str, *, actor_id: int | None = None, **payload: Any) -> None:
    """Fire-and-forget publish from domain code.

    Safe to call outside a running loop (becomes a no-op) and never raises into
    the caller — realtime must not be able to fail a write.
    """
    event = {"type": event_type, **payload}
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_safe_broadcast(event, actor_id))


async def _safe_broadcast(event: dict[str, Any], actor_id: int | None) -> None:
    try:
        await manager.broadcast(event, exclude_user=actor_id)
    except Exception:
        logger.exception("realtime broadcast failed")
