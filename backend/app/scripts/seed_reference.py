"""Idempotent seeding of reference data and the bootstrap admin.

Run on every startup (see entrypoint.sh). Safe to run repeatedly.

Reference data: issue statuses (the standard workflow), types, priorities.
Bootstrap admin: created only if there are no users yet, so the invite-only
system has a first administrator. Credentials come from env
BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD; in development a default admin
is created if those are unset.
"""
from __future__ import annotations

import asyncio
import os

from sqlalchemy import select

from app.auth.security import hash_password
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal
from app.models.enums import GlobalRole, StatusCategory
from app.models.notification import NotificationPreference
from app.models.reference import IssuePriority, IssueStatus, IssueType
from app.models.user import User

logger = get_logger("seed")

STATUSES = [
    ("backlog", "Backlog", StatusCategory.backlog, 0, "#94a3b8"),
    ("todo", "Todo", StatusCategory.todo, 1, "#64748b"),
    ("in_progress", "In Progress", StatusCategory.in_progress, 2, "#3b82f6"),
    ("resolved", "Resolved", StatusCategory.in_progress, 3, "#8b5cf6"),
    ("ready_for_qa", "Ready for QA", StatusCategory.in_progress, 4, "#f59e0b"),
    ("done", "Done", StatusCategory.done, 5, "#22c55e"),
]

TYPES = [
    ("task", "Task", "check-square", "#64748b"),
    ("bug", "Bug", "bug", "#ef4444"),
    ("feature", "Feature", "sparkles", "#8b5cf6"),
    ("improvement", "Improvement", "trending-up", "#3b82f6"),
    ("documentation", "Documentation", "book", "#14b8a6"),
    ("epic", "Epic", "layers", "#f59e0b"),
]

PRIORITIES = [
    ("urgent", "Urgent", 4, "#dc2626"),
    ("high", "High", 3, "#f97316"),
    ("medium", "Medium", 2, "#f59e0b"),
    ("low", "Low", 1, "#3b82f6"),
    ("none", "None", 0, "#94a3b8"),
]


async def _seed_reference(db) -> None:
    existing = {s.key for s in (await db.execute(select(IssueStatus))).scalars().all()}
    for key, name, category, order, color in STATUSES:
        if key not in existing:
            db.add(IssueStatus(key=key, name=name, category=category,
                               order_index=order, color=color))

    existing_t = {t.key for t in (await db.execute(select(IssueType))).scalars().all()}
    for key, name, icon, color in TYPES:
        if key not in existing_t:
            db.add(IssueType(key=key, name=name, icon=icon, color=color))

    existing_p = {p.key for p in (await db.execute(select(IssuePriority))).scalars().all()}
    for key, name, rank, color in PRIORITIES:
        if key not in existing_p:
            db.add(IssuePriority(key=key, name=name, rank=rank, color=color))


async def _seed_admin(db) -> None:
    count = (await db.execute(select(User))).scalars().first()
    if count is not None:
        return
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    name = os.getenv("BOOTSTRAP_ADMIN_NAME", "Administrator")
    if not (email and password):
        if settings.is_production:
            logger.warning(
                "No users and no BOOTSTRAP_ADMIN_EMAIL/PASSWORD set; "
                "skipping admin creation. Set them to bootstrap the first admin."
            )
            return
        email, password = "admin@lira.local", "Admin123!"
        logger.warning("Seeding development admin %s (change in production!)", email)
    admin = User(email=email.lower(), name=name, password_hash=hash_password(password),
                 role=GlobalRole.admin, is_active=True)
    db.add(admin)
    await db.flush()
    db.add(NotificationPreference(user_id=admin.id))
    logger.info("Bootstrap admin created: %s", email)


async def main() -> None:
    configure_logging()
    async with SessionLocal() as db:
        await _seed_reference(db)
        await _seed_admin(db)
        await db.commit()
    logger.info("Reference data seeded.")


if __name__ == "__main__":
    asyncio.run(main())
