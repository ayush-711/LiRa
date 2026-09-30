"""Issue relationships (blocks / blocked-by / relates-to)."""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import permissions
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.models.enums import RelationshipType
from app.models.issue_relationship import IssueRelationship
from app.models.user import User
from app.repositories.issue_repo import IssueRepository
from app.repositories.misc_repos import RelationshipRepository
from app.repositories.project_repo import ProjectRepository


class RelationshipService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = RelationshipRepository(db)
        self.issues = IssueRepository(db)
        self.projects = ProjectRepository(db)

    async def list_for_issue(self, issue_id: int) -> list[IssueRelationship]:
        return await self.repo.for_issue(issue_id)

    async def create(
        self, *, source_id: int, target_key: str, type: RelationshipType,
        actor: User, request: Request | None = None
    ) -> IssueRelationship:
        source = await self.issues.get(source_id)
        if source is None:
            raise NotFoundError("Source issue not found", code="ISSUE_NOT_FOUND")
        target = await self.issues.get_by_key(target_key)
        if target is None:
            raise NotFoundError(f"Issue {target_key} not found", code="ISSUE_NOT_FOUND")
        if target.id == source.id:
            raise ValidationError("An issue cannot relate to itself", code="RELATIONSHIP_SELF")

        project = await self.projects.get(source.project_id)
        member_role = await self.projects.member_role(source.project_id, actor.id)
        if not permissions.can_write_in_project(actor, project, member_role):
            raise PermissionDeniedError("You cannot modify this issue")

        if await self.repo.exists(source.id, target.id, type):
            raise ConflictError("That relationship already exists", code="RELATIONSHIP_EXISTS")

        # For symmetric relates_to, avoid storing the mirror twice.
        if type == RelationshipType.relates_to and await self.repo.exists(
            target.id, source.id, type
        ):
            raise ConflictError("That relationship already exists", code="RELATIONSHIP_EXISTS")

        # Basic cycle guard for blocks (A blocks B and B blocks A).
        if type == RelationshipType.blocks and await self.repo.exists(
            target.id, source.id, RelationshipType.blocks
        ):
            raise ValidationError("This would create a blocking cycle",
                                  code="RELATIONSHIP_CYCLE")

        rel = IssueRelationship(
            source_issue_id=source.id, target_issue_id=target.id,
            type=type, created_by_id=actor.id,
        )
        self.repo.add(rel)
        await self.db.commit()
        await self.db.refresh(rel)
        return rel

    async def delete(self, rel_id: int, *, actor: User) -> None:
        rel = await self.repo.get(rel_id)
        if rel is None:
            raise NotFoundError("Relationship not found", code="RELATIONSHIP_NOT_FOUND")
        source = await self.issues.get(rel.source_issue_id)
        project = await self.projects.get(source.project_id) if source else None
        member_role = (
            await self.projects.member_role(source.project_id, actor.id) if source else None
        )
        if not permissions.can_write_in_project(actor, project, member_role):
            raise PermissionDeniedError("You cannot modify this issue")
        await self.db.delete(rel)
        await self.db.commit()
