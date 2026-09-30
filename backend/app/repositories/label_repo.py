from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import IssueLabel, Label


class LabelRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, label_id: int) -> Label | None:
        return await self.db.get(Label, label_id)

    async def get_by_name(self, name: str) -> Label | None:
        result = await self.db.execute(
            select(Label).where(func.lower(Label.name) == name.lower())
        )
        return result.scalar_one_or_none()

    async def list(self, *, include_archived: bool = False) -> list[Label]:
        stmt = select(Label).order_by(Label.name)
        if not include_archived:
            stmt = stmt.where(Label.is_archived.is_(False))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_many(self, ids: list[int]) -> list[Label]:
        if not ids:
            return []
        result = await self.db.execute(select(Label).where(Label.id.in_(ids)))
        return list(result.scalars().all())

    async def links_for_issue(self, issue_id: int) -> list[IssueLabel]:
        result = await self.db.execute(
            select(IssueLabel).where(IssueLabel.issue_id == issue_id)
        )
        return list(result.scalars().all())

    def add(self, label: Label) -> None:
        self.db.add(label)

    def add_link(self, link: IssueLabel) -> None:
        self.db.add(link)

    async def delete_link(self, issue_id: int, label_id: int) -> None:
        link = (
            await self.db.execute(
                select(IssueLabel).where(
                    IssueLabel.issue_id == issue_id, IssueLabel.label_id == label_id
                )
            )
        ).scalar_one_or_none()
        if link:
            await self.db.delete(link)
