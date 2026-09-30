from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation


class InvitationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, invitation_id: int) -> Invitation | None:
        return await self.db.get(Invitation, invitation_id)

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        result = await self.db.execute(
            select(Invitation).where(Invitation.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_pending_by_email(self, email: str) -> Invitation | None:
        result = await self.db.execute(
            select(Invitation)
            .where(
                func.lower(Invitation.email) == email.lower(),
                Invitation.accepted_at.is_(None),
                Invitation.revoked_at.is_(None),
            )
            .order_by(Invitation.created_at.desc())
        )
        return result.scalars().first()

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[Invitation]:
        result = await self.db.execute(
            select(Invitation).order_by(Invitation.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    def add(self, invitation: Invitation) -> None:
        self.db.add(invitation)
