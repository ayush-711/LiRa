"""Attachment upload/download with safe local storage."""
from __future__ import annotations

from fastapi import Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import permissions
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.attachment import Attachment
from app.models.user import User
from app.repositories.issue_repo import IssueRepository
from app.repositories.misc_repos import AttachmentRepository
from app.repositories.project_repo import ProjectRepository
from app.services.activity_service import record_activity
from app.storage import files


class AttachmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AttachmentRepository(db)
        self.issues = IssueRepository(db)
        self.projects = ProjectRepository(db)

    async def list_for_issue(self, issue_id: int) -> list[Attachment]:
        return await self.repo.list_for_issue(issue_id)

    async def get_or_404(self, attachment_id: int) -> Attachment:
        att = await self.repo.get(attachment_id)
        if att is None:
            raise NotFoundError("Attachment not found", code="ATTACHMENT_NOT_FOUND")
        return att

    async def upload(self, *, issue_id: int, actor: User, upload: UploadFile,
                     request: Request | None = None) -> Attachment:
        issue = await self.issues.get(issue_id)
        if issue is None:
            raise NotFoundError("Issue not found", code="ISSUE_NOT_FOUND")
        project = await self.projects.get(issue.project_id)
        member_role = await self.projects.member_role(issue.project_id, actor.id)
        if not permissions.can_write_in_project(actor, project, member_role):
            raise PermissionDeniedError("You cannot attach files to this issue")

        data = await upload.read()
        files.validate_upload(upload.filename or "file", upload.content_type or "", len(data))
        rel_path = files.build_storage_path(issue.project_id, issue.id, upload.filename or "file")
        await files.save_bytes(rel_path, data)

        attachment = Attachment(
            issue_id=issue.id,
            original_filename=(upload.filename or "file")[:255],
            storage_path=rel_path,
            content_type=upload.content_type or "application/octet-stream",
            size_bytes=len(data),
            uploaded_by_id=actor.id,
        )
        self.repo.add(attachment)
        await record_activity(
            self.db, event_type="attachment.added", actor_id=actor.id,
            issue_id=issue.id, project_id=issue.project_id,
            new_value=attachment.original_filename,
        )
        await self.db.commit()
        await self.db.refresh(attachment)
        return attachment

    async def delete(self, attachment_id: int, *, actor: User) -> None:
        att = await self.get_or_404(attachment_id)
        issue = await self.issues.get(att.issue_id)
        member_role = await self.projects.member_role(issue.project_id, actor.id) if issue else None
        can = (
            permissions.is_admin(actor)
            or att.uploaded_by_id == actor.id
            or (issue and permissions.can_manage_project(actor, member_role))
        )
        if not can:
            raise PermissionDeniedError("You cannot delete this attachment")
        files.delete_file(att.storage_path)
        await self.db.delete(att)
        await self.db.commit()
