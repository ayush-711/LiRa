from __future__ import annotations

import asyncio

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import ACCESS_COOKIE
from app.auth.security import decode_token
from app.db.session import SessionLocal
from app.realtime.manager import manager
from app.repositories.user_repo import UserRepository

router = APIRouter(tags=["realtime"])


async def _authenticate(ws: WebSocket) -> int | None:
    """Resolve the user from the session cookie (or ?token= for API clients)."""
    token = ws.cookies.get(ACCESS_COOKIE) or ws.query_params.get("token")
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type="access")
    except jwt.PyJWTError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    async with SessionLocal() as db:  # type: AsyncSession
        user = await UserRepository(db).get(int(user_id))
        if user is None or not user.is_active:
            return None
        return user.id


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Live update stream.

    Events are cache-invalidation hints, not authoritative data — clients refetch
    from the REST API when they arrive. Visibility in V1 is global, so all
    authenticated users receive all events.
    """
    user_id = await _authenticate(ws)
    if user_id is None:
        await ws.close(code=4401)  # unauthorised
        return

    await manager.connect(user_id, ws)
    try:
        while True:
            # We don't expect client messages; this keeps the socket open and
            # detects disconnects. Respond to pings to keep proxies happy.
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        raise
    except Exception:
        pass
    finally:
        await manager.disconnect(user_id, ws)
