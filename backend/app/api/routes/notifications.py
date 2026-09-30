from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.user import User
from app.repositories.misc_repos import NotificationRepository
from app.schemas.common import MessageResponse
from app.schemas.misc import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    only_unread: bool = False, limit: int = 30, offset: int = 0,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[NotificationOut]:
    rows = await NotificationRepository(db).list_for_user(
        user.id, only_unread=only_unread, limit=limit, offset=offset
    )
    return [NotificationOut.model_validate(n) for n in rows]


@router.get("/unread-count", response_model=dict)
async def unread_count(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> dict:
    return {"count": await NotificationRepository(db).unread_count(user.id)}


@router.post("/{notification_id}/read", response_model=MessageResponse)
async def mark_read(
    notification_id: int, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    repo = NotificationRepository(db)
    n = await repo.get(notification_id)
    if n is None:
        raise NotFoundError("Notification not found", code="NOTIFICATION_NOT_FOUND")
    if n.user_id != user.id:
        raise PermissionDeniedError("Not your notification")
    n.is_read = True
    n.read_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()
    return MessageResponse(message="Marked read")


@router.post("/read-all", response_model=MessageResponse)
async def mark_all_read(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    repo = NotificationRepository(db)
    await repo.mark_all_read(user.id)
    await db.commit()
    return MessageResponse(message="All notifications marked read")
