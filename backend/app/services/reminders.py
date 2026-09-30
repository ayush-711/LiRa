"""Daily due-date reminders.

Scans for open, assigned issues that are due soon or already overdue and sends
the assignee an in-app notification plus (if they've opted in) an email.

Idempotency: ``issues.last_due_reminder_on`` records the date a reminder was
sent, so re-running the job on the same day is a no-op. This also means a single
run per day per issue even if the process restarts.

Deliberately implemented as an in-process asyncio loop rather than Celery/Redis —
the operational footprint stays tiny, which is the point of this deployment.
NOTE: with multiple backend replicas this job would run once per replica; either
keep a single replica or move it behind a leader lock before scaling out.
"""
from __future__ import annotations

import asyncio
import datetime as dt

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.enums import StatusCategory
from app.models.issue import Issue
from app.models.reference import IssueStatus
from app.notifications import templates
from app.services.notification_service import NotificationService

logger = get_logger("reminders")

# How far ahead counts as "due soon".
DUE_SOON_DAYS = 1


async def run_due_reminders(db, *, today: dt.date | None = None) -> int:
    """Send reminders for issues due within DUE_SOON_DAYS or already overdue.

    Returns the number of reminders sent.
    """
    today = today or dt.date.today()
    horizon = today + dt.timedelta(days=DUE_SOON_DAYS)

    stmt = (
        select(Issue)
        .join(IssueStatus, Issue.status_id == IssueStatus.id)
        .where(
            Issue.archived_at.is_(None),
            Issue.assignee_id.is_not(None),
            Issue.due_date.is_not(None),
            Issue.due_date <= horizon,
            IssueStatus.category != StatusCategory.done,
            or_(
                Issue.last_due_reminder_on.is_(None),
                Issue.last_due_reminder_on < today,
            ),
        )
        .options(
            selectinload(Issue.assignee),
            selectinload(Issue.project),
        )
    )
    issues = (await db.execute(stmt)).scalars().unique().all()
    if not issues:
        return 0

    notifier = NotificationService(db)
    sent = 0
    for issue in issues:
        assignee = issue.assignee
        if assignee is None or not assignee.is_active:
            continue
        overdue = issue.due_date < today
        email = templates.issue_due_reminder(
            issue.key, issue.title,
            issue.project.name if issue.project else "",
            issue.due_date.isoformat(), overdue,
        )
        await notifier.create(
            recipient=assignee,
            actor=None,
            type="overdue" if overdue else "due_soon",
            title=f"[{issue.key}] {'Overdue' if overdue else 'Due soon'}",
            body=issue.title,
            issue_id=issue.id,
            meta={"issue_key": issue.key, "due_date": issue.due_date.isoformat()},
            email=email,
            email_pref_attr="email_on_due_reminder",
        )
        issue.last_due_reminder_on = today
        sent += 1

    await db.commit()
    await notifier.flush()
    logger.info("Due-date reminders sent: %s", sent)
    return sent


async def reminder_loop() -> None:
    """Background loop started on application startup."""
    # Small delay so startup (migrations, seeding) settles first.
    await asyncio.sleep(30)
    interval = max(1, settings.due_reminder_interval_hours) * 3600
    while True:
        try:
            async with SessionLocal() as db:
                await run_due_reminders(db)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Due-date reminder run failed")
        await asyncio.sleep(interval)
