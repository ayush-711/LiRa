from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import activity_to_out
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.misc_repos import ActivityRepository
from app.schemas.misc import ActivityOut

router = APIRouter(prefix="/activity", tags=["activity"])

# The activity feed is a "what just happened" view, not an archive — the audit
# log is the durable record. Capping the page keeps the query cheap and the page
# readable; raise this deliberately rather than by accident.
MAX_FEED_ITEMS = 100


@router.get("", response_model=dict)
async def workspace_activity(
    limit: int = Query(20, ge=1, le=MAX_FEED_ITEMS),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Most recent activity across every project (newest first)."""
    repo = ActivityRepository(db)
    events = await repo.recent(limit=limit)
    return {
        "items": [activity_to_out(e).model_dump() for e in events],
        "returned": len(events),
        "total": await repo.count(),
        "max": MAX_FEED_ITEMS,
    }
