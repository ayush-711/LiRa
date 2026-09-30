"""Project lifecycle and membership management."""
from __future__ import annotations

import datetime as dt
import re

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import permissions
from app.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.models.enums import ProjectRole, ProjectStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.services.activity_service import record_activity
from app.services.audit_service import record_audit

KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")


class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ProjectRepository(db)
        self.users = UserRepository(db)

    async def get_or_404(self, project_id: int) -> Project:
        project = await self.repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found", code="PROJECT_NOT_FOUND")
        return project

    async def get_by_key_or_404(self, key: str) -> Project:
        project = await self.repo.get_by_key(key)
        if project is None:
            raise NotFoundError(f"Project {key} not found", code="PROJECT_NOT_FOUND")
        return project

    async def create(
        self,
        *,
        actor: User,
        name: str,
        key: str,
        description: str | None,
        lead_id: int | None,
        priority: str | None,
        start_date: dt.date | None,
        target_date: dt.date | None,
        request: Request,
    ) -> Project:
        if not permissions.can_create_project(actor):
            raise PermissionDeniedError("Only administrators can create projects")

        name = name.strip()
        key = key.strip().upper()
        if not name:
            raise ValidationError("Project name is required", code="NAME_REQUIRED")
        if not KEY_RE.match(key):
            raise ValidationError(
                "Project key must be 2–10 uppercase letters/digits starting with a letter",
                code="INVALID_PROJECT_KEY",
            )
        if await self.repo.get_by_key(key):
            raise ConflictError(f"Project key {key} is already in use",
                                code="PROJECT_KEY_TAKEN")

        if lead_id is not None and await self.users.get(lead_id) is None:
            raise ValidationError("Lead user not found", code="LEAD_NOT_FOUND")

        project = Project(
            name=name, key=key, description=description or None,
            lead_id=lead_id, created_by_id=actor.id, priority=priority,
            start_date=start_date, target_date=target_date,
            status=ProjectStatus.active,
        )
        self.repo.add(project)
        await self.db.flush()

        # Creator (and lead) become project managers by default.
        self.repo.add_member(ProjectMember(
            project_id=project.id, user_id=actor.id, role=ProjectRole.manager
        ))
        if lead_id and lead_id != actor.id:
            self.repo.add_member(ProjectMember(
                project_id=project.id, user_id=lead_id, role=ProjectRole.manager
            ))

        await record_activity(
            self.db, event_type="project.created", actor_id=actor.id,
            project_id=project.id, new_value=project.name,
        )
        await record_audit(
            self.db, action="project.created", actor_id=actor.id,
            entity_type="project", entity_id=project.id,
            meta={"key": key, "name": name}, request=request,
        )
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update(
        self, project: Project, *, actor: User, member_role: ProjectRole | None,
        changes: dict, request: Request
    ) -> Project:
        if not permissions.can_manage_project(actor, member_role):
            raise PermissionDeniedError("You cannot edit this project")
        for field in ("name", "description", "priority", "start_date", "target_date",
                      "lead_id", "status"):
            if field in changes and changes[field] is not None:
                setattr(project, field, changes[field])
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def archive(
        self, project: Project, *, actor: User, member_role: ProjectRole | None,
        request: Request
    ) -> Project:
        if not permissions.can_manage_project(actor, member_role):
            raise PermissionDeniedError("You cannot archive this project")
        project.status = ProjectStatus.archived
        project.archived_at = dt.datetime.now(dt.timezone.utc)
        await record_activity(
            self.db, event_type="project.archived", actor_id=actor.id,
            project_id=project.id,
        )
        await record_audit(
            self.db, action="project.archived", actor_id=actor.id,
            entity_type="project", entity_id=project.id, request=request,
        )
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def unarchive(
        self, project: Project, *, actor: User, member_role: ProjectRole | None,
        request: Request
    ) -> Project:
        """Restore an archived project to active. Admins only — a project manager
        loses their management surface once archived, so restoring is an admin act."""
        if not permissions.is_admin(actor):
            raise PermissionDeniedError("Only administrators can restore a project")
        project.status = ProjectStatus.active
        project.archived_at = None
        await record_activity(
            self.db, event_type="project.restored", actor_id=actor.id,
            project_id=project.id,
        )
        await record_audit(
            self.db, action="project.restored", actor_id=actor.id,
            entity_type="project", entity_id=project.id, request=request,
        )
        await self.db.commit()
        await self.db.refresh(project)
        return project

    # ── Membership ─────────────────────────────────────────────
    async def add_member(
        self, project: Project, *, user_id: int, role: ProjectRole,
        actor: User, actor_role: ProjectRole | None, request: Request
    ) -> ProjectMember:
        if not permissions.can_manage_project(actor, actor_role):
            raise PermissionDeniedError("You cannot manage this project's members")
        member_user = await self.users.get(user_id)
        if member_user is None or not member_user.is_active:
            raise ValidationError("User not found or inactive", code="USER_NOT_FOUND")
        if await self.repo.get_membership(project.id, user_id):
            raise ConflictError("User is already a member", code="ALREADY_MEMBER")
        member = ProjectMember(project_id=project.id, user_id=user_id, role=role)
        self.repo.add_member(member)
        await record_activity(
            self.db, event_type="project.member_added", actor_id=actor.id,
            project_id=project.id, new_value=member_user.name,
        )
        await record_audit(
            self.db, action="project.membership_changed", actor_id=actor.id,
            entity_type="project", entity_id=project.id,
            meta={"added": member_user.email, "role": role.value}, request=request,
        )
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(
        self, project: Project, *, user_id: int, actor: User,
        actor_role: ProjectRole | None, request: Request
    ) -> None:
        if not permissions.can_manage_project(actor, actor_role):
            raise PermissionDeniedError("You cannot manage this project's members")
        membership = await self.repo.get_membership(project.id, user_id)
        if membership is None:
            raise NotFoundError("Membership not found", code="MEMBERSHIP_NOT_FOUND")
        await self.db.delete(membership)
        await record_activity(
            self.db, event_type="project.member_removed", actor_id=actor.id,
            project_id=project.id,
        )
        await record_audit(
            self.db, action="project.membership_changed", actor_id=actor.id,
            entity_type="project", entity_id=project.id,
            meta={"removed_user_id": user_id}, request=request,
        )
        await self.db.commit()
