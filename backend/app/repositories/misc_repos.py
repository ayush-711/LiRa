"""Smaller repositories grouped together: activity, notifications, audit,
attachments, relationships, password-reset tokens."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity import ActivityEvent
from app.models.attachment import Attachment
from app.models.audit import AuditLog
from app.models.issue_relationship import IssueRelationship
from app.models.notification import Notification, NotificationPreference
from app.models.password_reset import PasswordResetToken


class ActivityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, event: ActivityEvent) -> None:
        self.db.add(event)

    async def for_issue(self, issue_id: int, *, limit: int = 100, offset: int = 0):
        result = await self.db.execute(
            select(ActivityEvent)
            .where(ActivityEvent.issue_id == issue_id)
            .options(selectinload(ActivityEvent.actor))
            .order_by(ActivityEvent.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def for_project(self, project_id: int, *, limit: int = 50, offset: int = 0):
        result = await self.db.execute(
            select(ActivityEvent)
            .where(ActivityEvent.project_id == project_id)
            .options(selectinload(ActivityEvent.actor))
            .order_by(ActivityEvent.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def recent(self, *, limit: int = 20):
        result = await self.db.execute(
            select(ActivityEvent)
            .options(selectinload(ActivityEvent.actor))
            .order_by(ActivityEvent.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        return int((await self.db.execute(select(func.count(ActivityEvent.id)))).scalar_one())


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, notification: Notification) -> None:
        self.db.add(notification)

    async def get(self, notification_id: int) -> Notification | None:
        return await self.db.get(Notification, notification_id)

    async def list_for_user(
        self, user_id: int, *, only_unread: bool = False, limit: int = 30, offset: int = 0
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .options(selectinload(Notification.actor))
            .order_by(Notification.created_at.desc())
            .limit(limit).offset(offset)
        )
        if only_unread:
            stmt = stmt.where(Notification.is_read.is_(False))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def unread_count(self, user_id: int) -> int:
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read.is_(False)
        )
        return int((await self.db.execute(stmt)).scalar_one())

    async def mark_all_read(self, user_id: int) -> None:
        from sqlalchemy import update

        await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=dt.datetime.now(dt.timezone.utc))
        )

    # Preferences
    async def get_preferences(self, user_id: int) -> NotificationPreference | None:
        result = await self.db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def add_preferences(self, prefs: NotificationPreference) -> None:
        self.db.add(prefs)


class AuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, entry: AuditLog) -> None:
        self.db.add(entry)

    async def list(
        self,
        *,
        actor_id: int | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        date_from: dt.datetime | None = None,
        date_to: dt.datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .options(selectinload(AuditLog.actor))
            .order_by(AuditLog.created_at.desc())
        )
        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if date_from:
            stmt = stmt.where(AuditLog.created_at >= date_from)
        if date_to:
            stmt = stmt.where(AuditLog.created_at <= date_to)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, **kwargs) -> int:
        stmt = select(func.count(AuditLog.id))
        if kwargs.get("actor_id") is not None:
            stmt = stmt.where(AuditLog.actor_id == kwargs["actor_id"])
        if kwargs.get("action"):
            stmt = stmt.where(AuditLog.action == kwargs["action"])
        if kwargs.get("entity_type"):
            stmt = stmt.where(AuditLog.entity_type == kwargs["entity_type"])
        return int((await self.db.execute(stmt)).scalar_one())


class AttachmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, attachment: Attachment) -> None:
        self.db.add(attachment)

    async def get(self, attachment_id: int) -> Attachment | None:
        return await self.db.get(Attachment, attachment_id)

    async def list_for_issue(self, issue_id: int) -> list[Attachment]:
        result = await self.db.execute(
            select(Attachment)
            .where(Attachment.issue_id == issue_id)
            .options(selectinload(Attachment.uploaded_by))
            .order_by(Attachment.created_at.desc())
        )
        return list(result.scalars().all())


class RelationshipRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, rel: IssueRelationship) -> None:
        self.db.add(rel)

    async def get(self, rel_id: int) -> IssueRelationship | None:
        return await self.db.get(IssueRelationship, rel_id)

    async def for_issue(self, issue_id: int) -> list[IssueRelationship]:
        result = await self.db.execute(
            select(IssueRelationship).where(
                or_(
                    IssueRelationship.source_issue_id == issue_id,
                    IssueRelationship.target_issue_id == issue_id,
                )
            )
        )
        return list(result.scalars().all())

    async def exists(self, source_id: int, target_id: int, type_) -> bool:
        stmt = select(func.count(IssueRelationship.id)).where(
            IssueRelationship.source_issue_id == source_id,
            IssueRelationship.target_issue_id == target_id,
            IssueRelationship.type == type_,
        )
        return int((await self.db.execute(stmt)).scalar_one()) > 0


class PasswordResetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, token: PasswordResetToken) -> None:
        self.db.add(token)

    async def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()
