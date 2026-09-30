"""Activity feed retention.

The activity feed is a rolling "what just happened" window, not an archive:
only the newest ``ACTIVITY_RETENTION_LIMIT`` events are kept and anything older
is deleted. Pruning runs immediately after each event is written, so the table
never exceeds the limit rather than being trimmed on a schedule.

Trade-off worth knowing: because the cap is global, a busy day can age out an
older issue's history from its detail page. The **audit log** is the permanent,
append-only record of who did what — it is never pruned. Raise
ACTIVITY_RETENTION_LIMIT if you want a deeper feed.
"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.activity import ActivityEvent

logger = get_logger("retention")


async def prune_activity_events(db: AsyncSession, *, limit: int | None = None) -> int:
    """Delete activity events beyond the newest ``limit``. Returns rows removed."""
    keep = limit if limit is not None else settings.activity_retention_limit
    if keep <= 0:
        return 0

    # Ids of the newest `keep` events; everything else goes.
    keep_ids = (
        select(ActivityEvent.id)
        .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
        .limit(keep)
        .scalar_subquery()
    )
    result = await db.execute(
        delete(ActivityEvent).where(ActivityEvent.id.not_in(keep_ids))
    )
    removed = result.rowcount or 0
    if removed:
        logger.info("Pruned %s activity event(s) beyond the %s most recent", removed, keep)
    return removed
