"""Issue lifecycle: creation (transactional keys), edits, board moves, subtasks,
archiving. Emits activity, audit and notifications consistently."""
from __future__ import annotations

import datetime as dt

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import permissions
from app.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.models.enums import ProjectRole, StatusCategory
from app.models.issue import Issue
from app.models.label import IssueLabel
from app.models.project import Project
from app.models.user import User
from app.notifications import templates
from app.realtime.manager import publish
from app.repositories.issue_repo import IssueRepository
from app.repositories.label_repo import LabelRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.reference_repo import ReferenceRepository
from app.repositories.user_repo import UserRepository
from app.services.activity_service import record_activity
from app.services.audit_service import record_audit
from app.services.notification_service import NotificationService


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class IssueService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.issues = IssueRepository(db)
        self.projects = ProjectRepository(db)
        self.ref = ReferenceRepository(db)
        self.users = UserRepository(db)
        self.labels = LabelRepository(db)
        self.notifier = NotificationService(db)

    # ── Lookups ────────────────────────────────────────────────
    async def get_or_404(self, issue_id: int) -> Issue:
        issue = await self.issues.get_display(issue_id)
        if issue is None:
            raise NotFoundError("Issue not found", code="ISSUE_NOT_FOUND")
        return issue

    async def get_by_key_or_404(self, key: str) -> Issue:
        issue = await self.issues.get_by_key(key)
        if issue is None:
            raise NotFoundError(f"Issue {key} was not found", code="ISSUE_NOT_FOUND")
        return issue

    async def _member_role(self, project_id: int, user_id: int) -> ProjectRole | None:
        return await self.projects.member_role(project_id, user_id)

    async def _validate_assignee(self, project: Project, assignee_id: int | None) -> None:
        if assignee_id is None:
            return
        user = await self.users.get(assignee_id)
        if user is None or not user.is_active:
            raise ValidationError("Assignee must be an active user",
                                  code="INVALID_ASSIGNEE")
        role = await self.projects.member_role(project.id, assignee_id)
        if role is None and user.role.value != "admin":
            raise ValidationError("Assignee must be a member of the project",
                                  code="ASSIGNEE_NOT_MEMBER")

    # ── Creation ───────────────────────────────────────────────
    async def create(
        self,
        *,
        actor: User,
        project: Project,
        title: str,
        description: str | None = None,
        type_id: int | None = None,
        status_id: int | None = None,
        priority_id: int | None = None,
        assignee_id: int | None = None,
        due_date: dt.date | None = None,
        estimate: int | None = None,
        parent_id: int | None = None,
        label_ids: list[int] | None = None,
        request: Request | None = None,
    ) -> Issue:
        member_role = await self._member_role(project.id, actor.id)
        if not permissions.can_create_issue(actor, project, member_role):
            raise PermissionDeniedError("You cannot create issues in this project")

        title = title.strip()
        if not title:
            raise ValidationError("Title is required", code="TITLE_REQUIRED")
        if len(title) > 300:
            raise ValidationError("Title is too long", code="TITLE_TOO_LONG")

        issue_type = (await self.ref.type(type_id)) if type_id else await self.ref.type_by_key("task")
        status = (await self.ref.status(status_id)) if status_id else await self.ref.default_status()
        priority = (await self.ref.priority(priority_id)) if priority_id else await self.ref.default_priority()
        if not (issue_type and status and priority):
            raise ValidationError("Reference data missing; run reference seeding",
                                  code="REFERENCE_DATA_MISSING")

        await self._validate_assignee(project, assignee_id)

        if parent_id is not None:
            parent = await self.issues.get(parent_id)
            if parent is None or parent.project_id != project.id:
                raise ValidationError("Parent issue not found in this project",
                                      code="INVALID_PARENT")

        # Transactional issue-key allocation under a row lock on the project.
        locked = await self.projects.get_locked_for_key(project.id)
        assert locked is not None
        locked.issue_counter += 1
        number = locked.issue_counter
        key = f"{locked.key}-{number}"

        rank = await self.issues.max_board_rank(project.id, status.id) + 1.0

        issue = Issue(
            project_id=project.id, number=number, key=key, title=title,
            description=description or None, type_id=issue_type.id,
            status_id=status.id, priority_id=priority.id, assignee_id=assignee_id,
            reporter_id=actor.id, parent_id=parent_id, due_date=due_date,
            estimate=estimate, board_rank=rank,
        )
        if status.category == StatusCategory.done:
            issue.completed_at = _now()
        self.issues.add(issue)
        await self.db.flush()

        # Labels
        for lid in await self._resolve_label_ids(label_ids):
            self.db.add(IssueLabel(issue_id=issue.id, label_id=lid))

        await record_activity(
            self.db, event_type="issue.created", actor_id=actor.id,
            issue_id=issue.id, project_id=project.id, new_value=issue.key,
        )
        await record_audit(
            self.db, action="issue.created", actor_id=actor.id, entity_type="issue",
            entity_id=issue.id, meta={"key": key}, request=request,
        )

        if assignee_id and assignee_id != actor.id:
            await self._notify_assignment(issue, project, actor, assignee_id, priority.name)

        await self.db.commit()
        await self.notifier.flush()
        publish("issue.created", actor_id=actor.id, issue_key=issue.key,
                project_id=project.id)
        return await self.get_or_404(issue.id)

    async def _resolve_label_ids(self, label_ids: list[int] | None) -> list[int]:
        if not label_ids:
            return []
        labels = await self.labels.get_many(label_ids)
        return [l.id for l in labels]

    async def _notify_assignment(self, issue, project, actor, assignee_id, priority_name):
        assignee = await self.users.get(assignee_id)
        if not assignee:
            return
        email = templates.issue_assigned(
            issue.key, issue.title, project.name, priority_name,
            issue.due_date.isoformat() if issue.due_date else None, actor.name,
        )
        await self.notifier.create(
            recipient=assignee, actor=actor, type="issue_assigned",
            title=f"[{issue.key}] Assigned to you",
            body=issue.title, issue_id=issue.id, meta={"issue_key": issue.key},
            email=email, email_pref_attr="email_on_assignment",
        )

    # ── Update ─────────────────────────────────────────────────
    async def update(
        self, issue: Issue, *, actor: User, changes: dict, request: Request | None = None
    ) -> Issue:
        project = await self.projects.get(issue.project_id)
        assert project is not None
        member_role = await self._member_role(project.id, actor.id)
        if not permissions.can_write_in_project(actor, project, member_role):
            raise PermissionDeniedError("You cannot edit this issue")

        if "title" in changes and changes["title"] is not None:
            title = changes["title"].strip()
            if not title:
                raise ValidationError("Title is required", code="TITLE_REQUIRED")
            issue.title = title
        if "description" in changes:
            issue.description = changes["description"] or None
        if "due_date" in changes:
            issue.due_date = changes["due_date"]
        if "estimate" in changes:
            issue.estimate = changes["estimate"]

        if changes.get("type_id"):
            t = await self.ref.type(changes["type_id"])
            if not t:
                raise ValidationError("Invalid issue type", code="INVALID_TYPE")
            issue.type_id = t.id
            issue.type = t

        # Priority
        if changes.get("priority_id") and changes["priority_id"] != issue.priority_id:
            old = await self.ref.priority(issue.priority_id)
            new = await self.ref.priority(changes["priority_id"])
            if not new:
                raise ValidationError("Invalid priority", code="INVALID_PRIORITY")
            issue.priority_id = new.id
            issue.priority = new
            await record_activity(
                self.db, event_type="issue.priority_changed", actor_id=actor.id,
                issue_id=issue.id, project_id=project.id, field="priority",
                old_value=old.name if old else None, new_value=new.name,
            )

        # Assignee
        if "assignee_id" in changes and changes["assignee_id"] != issue.assignee_id:
            new_assignee_id = changes["assignee_id"]
            await self._validate_assignee(project, new_assignee_id)
            old_assignee = await self.users.get(issue.assignee_id) if issue.assignee_id else None
            issue.assignee_id = new_assignee_id
            issue.assignee = await self.users.get(new_assignee_id) if new_assignee_id else None
            await record_activity(
                self.db, event_type="issue.assigned", actor_id=actor.id,
                issue_id=issue.id, project_id=project.id, field="assignee",
                old_value=old_assignee.name if old_assignee else None,
                new_value=(await self.users.get(new_assignee_id)).name if new_assignee_id else None,
            )
            if new_assignee_id and new_assignee_id != actor.id:
                pr = await self.ref.priority(issue.priority_id)
                await self._notify_assignment(issue, project, actor, new_assignee_id, pr.name if pr else "")

        # Status
        if changes.get("status_id") and changes["status_id"] != issue.status_id:
            await self._apply_status_change(issue, project, actor, changes["status_id"])

        # Labels (full replace when provided)
        if "label_ids" in changes and changes["label_ids"] is not None:
            await self._replace_labels(issue, project, actor, changes["label_ids"])

        await self.db.commit()
        await self.notifier.flush()
        publish("issue.updated", actor_id=actor.id, issue_key=issue.key,
                project_id=project.id)
        return await self.get_or_404(issue.id)

    async def _apply_status_change(self, issue: Issue, project: Project, actor: User,
                                   new_status_id: int) -> None:
        old = await self.ref.status(issue.status_id)
        new = await self.ref.status(new_status_id)
        if not new:
            raise ValidationError("Invalid status", code="INVALID_STATUS")
        issue.status_id = new.id
        issue.status = new  # keep in-memory relationship consistent
        # Maintain resolved/completed timestamps by category.
        if new.category == StatusCategory.done:
            issue.completed_at = issue.completed_at or _now()
            issue.resolved_at = issue.resolved_at or _now()
        else:
            issue.completed_at = None
        issue.board_rank = await self.issues.max_board_rank(project.id, new.id) + 1.0
        await record_activity(
            self.db, event_type="issue.status_changed", actor_id=actor.id,
            issue_id=issue.id, project_id=project.id, field="status",
            old_value=old.name if old else None, new_value=new.name,
        )
        # Notify assignee (if configured and not the actor)
        if issue.assignee_id and issue.assignee_id != actor.id:
            assignee = await self.users.get(issue.assignee_id)
            if assignee:
                email = templates.issue_status_changed(
                    issue.key, issue.title, actor.name,
                    old.name if old else "?", new.name,
                )
                await self.notifier.create(
                    recipient=assignee, actor=actor, type="status_changed",
                    title=f"[{issue.key}] {new.name}", body=issue.title,
                    issue_id=issue.id, meta={"issue_key": issue.key}, email=email,
                    email_pref_attr="email_on_status_change",
                )

    async def _replace_labels(self, issue, project, actor, label_ids: list[int]) -> None:
        current = {l.label_id for l in await self.labels.links_for_issue(issue.id)}
        target = set(await self._resolve_label_ids(label_ids))
        for lid in target - current:
            self.db.add(IssueLabel(issue_id=issue.id, label_id=lid))
        for lid in current - target:
            await self.labels.delete_link(issue.id, lid)

    # ── Board move ─────────────────────────────────────────────
    async def move(
        self, issue: Issue, *, actor: User, status_id: int, rank: float | None,
        request: Request | None = None
    ) -> Issue:
        project = await self.projects.get(issue.project_id)
        assert project is not None
        member_role = await self._member_role(project.id, actor.id)
        if not permissions.can_write_in_project(actor, project, member_role):
            raise PermissionDeniedError("You cannot move this issue")

        if status_id != issue.status_id:
            await self._apply_status_change(issue, project, actor, status_id)
        if rank is not None:
            issue.board_rank = rank
        await self.db.commit()
        await self.notifier.flush()
        publish("issue.moved", actor_id=actor.id, issue_key=issue.key,
                project_id=project.id)
        return await self.get_or_404(issue.id)

    # ── Archive ────────────────────────────────────────────────
    async def archive(self, issue: Issue, *, actor: User, request: Request | None = None) -> Issue:
        project = await self.projects.get(issue.project_id)
        assert project is not None
        member_role = await self._member_role(project.id, actor.id)
        if not (permissions.is_admin(actor) or permissions.can_manage_project(actor, member_role)):
            raise PermissionDeniedError("You cannot archive this issue")
        issue.archived_at = _now()
        await record_activity(
            self.db, event_type="issue.archived", actor_id=actor.id,
            issue_id=issue.id, project_id=project.id,
        )
        await record_audit(
            self.db, action="issue.archived", actor_id=actor.id, entity_type="issue",
            entity_id=issue.id, request=request,
        )
        await self.db.commit()
        publish("issue.archived", actor_id=actor.id, issue_key=issue.key,
                project_id=project.id)
        return await self.get_or_404(issue.id)
