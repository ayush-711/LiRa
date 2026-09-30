from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ProjectRole, ProjectStatus
from app.models.project import Project
from app.models.project_member import ProjectMember


class ProjectRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, project_id: int) -> Project | None:
        return await self.db.get(Project, project_id)

    async def get_by_key(self, key: str) -> Project | None:
        result = await self.db.execute(
            select(Project).where(func.upper(Project.key) == key.upper())
        )
        return result.scalar_one_or_none()

    async def get_locked_for_key(self, project_id: int) -> Project | None:
        """Row-locked fetch used when allocating the next issue number."""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def list(
        self, *, include_archived: bool = False, limit: int = 100, offset: int = 0
    ) -> list[Project]:
        stmt = select(Project).order_by(Project.name)
        if not include_archived:
            stmt = stmt.where(Project.status != ProjectStatus.archived)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, include_archived: bool = False) -> int:
        stmt = select(func.count(Project.id))
        if not include_archived:
            stmt = stmt.where(Project.status != ProjectStatus.archived)
        return int((await self.db.execute(stmt)).scalar_one())

    # ── Membership ─────────────────────────────────────────────
    async def get_membership(self, project_id: int, user_id: int) -> ProjectMember | None:
        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def member_role(self, project_id: int, user_id: int) -> ProjectRole | None:
        m = await self.get_membership(project_id, user_id)
        return m.role if m else None

    async def list_members(self, project_id: int) -> list[ProjectMember]:
        result = await self.db.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .options(selectinload(ProjectMember.user))
            .order_by(ProjectMember.role)
        )
        return list(result.scalars().all())

    def add(self, project: Project) -> None:
        self.db.add(project)

    def add_member(self, member: ProjectMember) -> None:
        self.db.add(member)
