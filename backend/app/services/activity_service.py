"""User-facing activity feed events.

Stores structured fields; the API renders human-readable sentences from them
(see app.services.activity_render). Activity is immutable once written.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityEvent
from app.repositories.misc_repos import ActivityRepository
from app.services.retention import prune_activity_events


async def record_activity(
    db: AsyncSession,
    *,
    event_type: str,
    actor_id: int | None,
    issue_id: int | None = None,
    project_id: int | None = None,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    meta: dict | None = None,
) -> ActivityEvent:
    event = ActivityEvent(
        event_type=event_type,
        actor_id=actor_id,
        issue_id=issue_id,
        project_id=project_id,
        field=field,
        old_value=old_value,
        new_value=new_value,
        meta=meta,
    )
    ActivityRepository(db).add(event)
    # Flush so the new row is visible to the retention query, then trim the
    # feed back to its cap. Both happen inside the caller's transaction.
    await db.flush()
    await prune_activity_events(db)
    return event
