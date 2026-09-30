"""Append-only audit logging for security/administrative actions."""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.misc_repos import AuditRepository


def _client_meta(request: Request | None) -> tuple[str | None, str | None]:
    if request is None:
        return None, None
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    ua = request.headers.get("user-agent")
    return ip, (ua[:400] if ua else None)


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    actor_id: int | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    meta: dict | None = None,
    request: Request | None = None,
) -> AuditLog:
    ip, ua = _client_meta(request)
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        meta=meta,
        ip_address=ip,
        user_agent=ua,
    )
    AuditRepository(db).add(entry)
    return entry
