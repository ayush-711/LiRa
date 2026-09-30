"""Comments with @mentions, notifications and activity."""
from __future__ import annotations

import datetime as dt
import re

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import permissions
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.models.comment import Comment
from app.models.user import User
from app.notifications import templates
from app.realtime.manager import publish
from app.repositories.comment_repo import CommentRepository
from app.repositories.issue_repo import IssueRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.services.activity_service import record_activity
from app.services.notification_service import NotificationService

MENTION_RE = re.compile(r"@([A-Za-z0-9._-]+)")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _snippet(text: str, n: int = 140) -> str:
    text = " ".join(text.split())
    return text[:n] + ("…" if len(text) > n else "")


class CommentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CommentRepository(db)
        self.issues = IssueRepository(db)
        self.projects = ProjectRepository(db)
        self.users = UserRepository(db)
        self.notifier = NotificationService(db)

    async def list_for_issue(self, issue_id: int, **kw):
        return await self.repo.list_for_issue(issue_id, **kw)

    async def _resolve_mentions(self, body: str) -> list[User]:
        handles = {m.lower() for m in MENTION_RE.findall(body)}
        if not handles:
            return []
        # Match against the local-part of email or a name-token.
        result = await self.users.list(include_inactive=False, limit=500)
        mentioned = []
        for u in result:
            local = u.email.split("@")[0].lower()
            name_token = u.name.replace(" ", "").lower()
            if local in handles or name_token in handles:
                mentioned.append(u)
        return mentioned

    async def create(self, *, issue_id: int, actor: User, body: str,
                     request: Request | None = None) -> Comment:
        body = body.strip()
        if not body:
            raise ValidationError("Comment cannot be empty", code="COMMENT_EMPTY")
        issue = await self.issues.get_display(issue_id)
        if issue is None:
            raise NotFoundError("Issue not found", code="ISSUE_NOT_FOUND")
        project = await self.projects.get(issue.project_id)
        member_role = await self.projects.member_role(issue.project_id, actor.id)
        if not permissions.can_comment(actor, project, member_role):
            raise PermissionDeniedError("You cannot comment on this issue")

        comment = Comment(issue_id=issue_id, author_id=actor.id, body=body)
        self.repo.add(comment)
        await record_activity(
            self.db, event_type="comment.added", actor_id=actor.id,
            issue_id=issue_id, project_id=issue.project_id,
        )

        mentioned = await self._resolve_mentions(body)
        mentioned_ids = {u.id for u in mentioned}

        # Notify mentioned users
        for user in mentioned:
            email = templates.issue_mention(issue.key, issue.title, actor.name, _snippet(body))
            await self.notifier.create(
                recipient=user, actor=actor, type="mention",
                title=f"[{issue.key}] {actor.name} mentioned you", body=_snippet(body),
                issue_id=issue_id, meta={"issue_key": issue.key},
                email=email, email_pref_attr="email_on_mention",
            )

        # Notify assignee + reporter (participants) if not the actor and not already mentioned
        participant_ids = {issue.assignee_id, issue.reporter_id} - {None, actor.id} - mentioned_ids
        for uid in participant_ids:
            user = await self.users.get(uid)
            if not user:
                continue
            email = templates.issue_comment(issue.key, issue.title, actor.name, _snippet(body))
            await self.notifier.create(
                recipient=user, actor=actor, type="comment",
                title=f"[{issue.key}] New comment", body=_snippet(body),
                issue_id=issue_id, meta={"issue_key": issue.key},
                email=email, email_pref_attr="email_on_comment",
            )

        await self.db.commit()
        await self.notifier.flush()
        publish("comment.added", actor_id=actor.id, issue_key=issue.key,
                project_id=issue.project_id)
        await self.db.refresh(comment)
        return comment

    async def update(self, comment_id: int, *, actor: User, body: str) -> Comment:
        comment = await self.repo.get(comment_id)
        if comment is None or comment.deleted_at is not None:
            raise NotFoundError("Comment not found", code="COMMENT_NOT_FOUND")
        if not permissions.can_edit_comment(actor, comment.author_id):
            raise PermissionDeniedError("You can only edit your own comments")
        body = body.strip()
        if not body:
            raise ValidationError("Comment cannot be empty", code="COMMENT_EMPTY")
        comment.body = body
        comment.edited_at = _now()
        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def delete(self, comment_id: int, *, actor: User) -> None:
        comment = await self.repo.get(comment_id)
        if comment is None or comment.deleted_at is not None:
            raise NotFoundError("Comment not found", code="COMMENT_NOT_FOUND")
        if not permissions.can_edit_comment(actor, comment.author_id):
            raise PermissionDeniedError("You can only delete your own comments")
        comment.deleted_at = _now()
        await self.db.commit()
