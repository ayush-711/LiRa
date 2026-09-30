from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StatusCategory
from app.models.reference import IssuePriority, IssueStatus, IssueType


class ReferenceRepository:
    """Access to workflow reference data (statuses, types, priorities)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def statuses(self) -> list[IssueStatus]:
        result = await self.db.execute(
            select(IssueStatus).where(IssueStatus.is_active.is_(True))
            .order_by(IssueStatus.order_index)
        )
        return list(result.scalars().all())

    async def types(self) -> list[IssueType]:
        result = await self.db.execute(
            select(IssueType).where(IssueType.is_active.is_(True)).order_by(IssueType.id)
        )
        return list(result.scalars().all())

    async def priorities(self) -> list[IssuePriority]:
        result = await self.db.execute(
            select(IssuePriority).where(IssuePriority.is_active.is_(True))
            .order_by(IssuePriority.rank.desc())
        )
        return list(result.scalars().all())

    async def status(self, status_id: int) -> IssueStatus | None:
        return await self.db.get(IssueStatus, status_id)

    async def status_by_key(self, key: str) -> IssueStatus | None:
        result = await self.db.execute(select(IssueStatus).where(IssueStatus.key == key))
        return result.scalar_one_or_none()

    async def default_status(self) -> IssueStatus | None:
        # "Todo" is the default for quick-create per the spec.
        return await self.status_by_key("todo")

    async def first_status_in(self, category: StatusCategory) -> IssueStatus | None:
        result = await self.db.execute(
            select(IssueStatus).where(IssueStatus.category == category)
            .order_by(IssueStatus.order_index)
        )
        return result.scalars().first()

    async def type(self, type_id: int) -> IssueType | None:
        return await self.db.get(IssueType, type_id)

    async def type_by_key(self, key: str) -> IssueType | None:
        result = await self.db.execute(select(IssueType).where(IssueType.key == key))
        return result.scalar_one_or_none()

    async def priority(self, priority_id: int) -> IssuePriority | None:
        return await self.db.get(IssuePriority, priority_id)

    async def priority_by_key(self, key: str) -> IssuePriority | None:
        result = await self.db.execute(
            select(IssuePriority).where(IssuePriority.key == key)
        )
        return result.scalar_one_or_none()

    async def default_priority(self) -> IssuePriority | None:
        return await self.priority_by_key("none")
