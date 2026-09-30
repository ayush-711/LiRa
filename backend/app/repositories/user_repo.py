from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: int) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def list(
        self, *, include_inactive: bool = True, limit: int = 100, offset: int = 0
    ) -> list[User]:
        stmt = select(User).order_by(User.name)
        if not include_inactive:
            stmt = stmt.where(User.is_active.is_(True))
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, include_inactive: bool = True) -> int:
        stmt = select(func.count(User.id))
        if not include_inactive:
            stmt = stmt.where(User.is_active.is_(True))
        return int((await self.db.execute(stmt)).scalar_one())

    def add(self, user: User) -> None:
        self.db.add(user)
