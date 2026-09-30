from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_admin
from app.models.user import User
from app.repositories.misc_repos import AuditRepository
from app.schemas.common import Page
from app.schemas.misc import AuditOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=Page[AuditOut])
async def list_audit_logs(
    actor_id: int | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    date_from: dt.datetime | None = None,
    date_to: dt.datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Page[AuditOut]:
    repo = AuditRepository(db)
    rows = await repo.list(
        actor_id=actor_id, action=action, entity_type=entity_type,
        date_from=date_from, date_to=date_to, limit=limit, offset=offset,
    )
    total = await repo.count(actor_id=actor_id, action=action, entity_type=entity_type)
    return Page(
        items=[AuditOut.model_validate(r) for r in rows],
        total=total, limit=limit, offset=offset,
    )
