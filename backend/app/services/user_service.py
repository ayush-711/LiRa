"""User management (admin) and self-service account updates."""
from __future__ import annotations

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password, verify_password
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.models.enums import GlobalRole
from app.models.issue import Issue
from app.models.reference import IssueStatus
from app.models.enums import StatusCategory
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.audit_service import record_audit
from app.services.password_policy import validate_password


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)

    async def get_or_404(self, user_id: int) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found", code="USER_NOT_FOUND")
        return user

    async def update_role(
        self, user_id: int, role: GlobalRole, *, actor: User, request: Request
    ) -> User:
        user = await self.get_or_404(user_id)
        if user.id == actor.id and role != GlobalRole.admin:
            raise ValidationError("You cannot remove your own admin role",
                                  code="CANNOT_DEMOTE_SELF")
        old = user.role
        user.role = role
        await record_audit(
            self.db, action="role.changed", actor_id=actor.id, entity_type="user",
            entity_id=user.id, meta={"from": old.value, "to": role.value}, request=request,
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def set_active(
        self, user_id: int, active: bool, *, actor: User, request: Request
    ) -> User:
        user = await self.get_or_404(user_id)
        if user.id == actor.id and not active:
            raise ValidationError("You cannot deactivate your own account",
                                  code="CANNOT_DEACTIVATE_SELF")
        user.is_active = active
        await record_audit(
            self.db, action="user.deactivated" if not active else "user.reactivated",
            actor_id=actor.id, entity_type="user", entity_id=user.id, request=request,
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_profile(self, user: User, *, name: str | None,
                             avatar_url: str | None) -> User:
        if name is not None:
            name = name.strip()
            if not name:
                raise ValidationError("Name cannot be empty", code="NAME_REQUIRED")
            user.name = name
        if avatar_url is not None:
            user.avatar_url = avatar_url or None
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def change_password(self, user: User, *, current: str, new: str) -> None:
        if not verify_password(current, user.password_hash):
            raise PermissionDeniedError("Current password is incorrect",
                                        code="INVALID_CURRENT_PASSWORD")
        validate_password(new)
        user.password_hash = hash_password(new)
        await self.db.commit()

    async def workload_stats(self) -> dict[int, dict[str, int]]:
        """Per-user counts: assigned (open), overdue, in progress. One grouped query
        each to avoid N+1."""
        import datetime as dt

        stats: dict[int, dict[str, int]] = {}

        def _bucket(uid):
            return stats.setdefault(uid, {"assigned": 0, "in_progress": 0, "overdue": 0})

        # assigned open (not done, not archived)
        base = (
            select(Issue.assignee_id, func.count(Issue.id))
            .join(IssueStatus, Issue.status_id == IssueStatus.id)
            .where(
                Issue.assignee_id.is_not(None),
                Issue.archived_at.is_(None),
                IssueStatus.category != StatusCategory.done,
            )
            .group_by(Issue.assignee_id)
        )
        for uid, n in (await self.db.execute(base)).all():
            _bucket(uid)["assigned"] = n

        in_prog = base.where(IssueStatus.category == StatusCategory.in_progress)
        for uid, n in (await self.db.execute(in_prog)).all():
            _bucket(uid)["in_progress"] = n

        overdue = (
            select(Issue.assignee_id, func.count(Issue.id))
            .join(IssueStatus, Issue.status_id == IssueStatus.id)
            .where(
                Issue.assignee_id.is_not(None),
                Issue.archived_at.is_(None),
                IssueStatus.category != StatusCategory.done,
                Issue.due_date.is_not(None),
                Issue.due_date < dt.date.today(),
            )
            .group_by(Issue.assignee_id)
        )
        for uid, n in (await self.db.execute(overdue)).all():
            _bucket(uid)["overdue"] = n

        return stats
