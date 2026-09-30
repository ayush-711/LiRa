from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment


class CommentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, comment_id: int) -> Comment | None:
        return await self.db.get(Comment, comment_id)

    async def list_for_issue(
        self, issue_id: int, *, limit: int = 100, offset: int = 0
    ) -> list[Comment]:
        result = await self.db.execute(
            select(Comment)
            .where(Comment.issue_id == issue_id, Comment.deleted_at.is_(None))
            .options(selectinload(Comment.author))
            .order_by(Comment.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_for_issue(self, issue_id: int) -> int:
        stmt = select(func.count(Comment.id)).where(
            Comment.issue_id == issue_id, Comment.deleted_at.is_(None)
        )
        return int((await self.db.execute(stmt)).scalar_one())

    def add(self, comment: Comment) -> None:
        self.db.add(comment)
