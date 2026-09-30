"""Development seed data. NOT run in production automatically.

Creates sample users, a project, labels, issues, a comment and a subtask that
mirror the acceptance scenario, so the app is immediately explorable.

Usage:  python -m app.scripts.seed_dev_data
"""
from __future__ import annotations

import asyncio
import datetime as dt

from sqlalchemy import select

from app.auth.security import hash_password
from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal
from app.models.enums import GlobalRole, ProjectRole
from app.models.label import Label
from app.models.notification import NotificationPreference
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.repositories.reference_repo import ReferenceRepository
from app.services.issue_service import IssueService

logger = get_logger("seed-dev")

SAMPLE_USERS = [
    ("rahul@lira.local", "Rahul Kumar", GlobalRole.project_manager),
    ("priya@lira.local", "Priya Sharma", GlobalRole.member),
    ("aman@lira.local", "Aman Verma", GlobalRole.member),
]


async def _get_or_create_user(db, email, name, role) -> User:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user:
        return user
    user = User(email=email, name=name, password_hash=hash_password("Password123!"),
                role=role, is_active=True)
    db.add(user)
    await db.flush()
    db.add(NotificationPreference(user_id=user.id))
    return user


async def main() -> None:
    configure_logging()
    async with SessionLocal() as db:
        admin = (await db.execute(
            select(User).where(User.role == GlobalRole.admin)
        )).scalars().first()
        if admin is None:
            logger.error("No admin found. Run seed_reference first.")
            return

        if (await db.execute(select(Project).where(Project.key == "DOC"))).scalar_one_or_none():
            logger.info("Dev data already present (project DOC exists). Skipping.")
            return

        users = [await _get_or_create_user(db, *u) for u in SAMPLE_USERS]
        rahul, priya, aman = users

        # Labels
        labels = {}
        for name, color in [("OCR", "#6d6a8a"), ("ML", "#5f7a86"),
                            ("Backend", "#6b7a5e"), ("Frontend", "#9c7b3f"),
                            ("Production", "#a15c4e")]:
            label = Label(name=name, color=color, created_by_id=admin.id)
            db.add(label)
            await db.flush()
            labels[name] = label

        # Project
        project = Project(key="DOC", name="Document AI", description="OCR & document intelligence.",
                          lead_id=rahul.id, created_by_id=admin.id)
        db.add(project)
        await db.flush()
        for u, role in [(admin, ProjectRole.manager), (rahul, ProjectRole.manager),
                        (priya, ProjectRole.member), (aman, ProjectRole.member)]:
            db.add(ProjectMember(project_id=project.id, user_id=u.id, role=role))
        await db.commit()

        ref = ReferenceRepository(db)
        bug = await ref.type_by_key("bug")
        task = await ref.type_by_key("task")
        high = await ref.priority_by_key("high")
        todo = await ref.status_by_key("todo")

        svc = IssueService(db)
        await db.refresh(project)

        issue = await svc.create(
            actor=rahul, project=project,
            title="Fix OCR extraction for cheque amount",
            description="Amounts on scanned cheques are misread. Improve preprocessing.",
            type_id=bug.id, priority_id=high.id, status_id=todo.id,
            assignee_id=priya.id, due_date=dt.date(2026, 9, 12),
            label_ids=[labels["OCR"].id, labels["ML"].id],
        )
        # A couple more for a fuller board
        await svc.create(actor=rahul, project=project, title="Add batch OCR endpoint",
                         type_id=task.id, assignee_id=aman.id,
                         label_ids=[labels["Backend"].id])
        await svc.create(actor=priya, project=project, title="Improve OCR preprocessing pipeline",
                         type_id=task.id, parent_id=issue.id,
                         label_ids=[labels["ML"].id])

        logger.info("Dev data seeded: project DOC with %s and sample issues.",
                    ", ".join(u.name for u in users))


if __name__ == "__main__":
    asyncio.run(main())
