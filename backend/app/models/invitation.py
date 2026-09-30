from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import GlobalRole


class Invitation(Base, TimestampMixin):
    """Invitation-only registration record.

    The raw token is emailed to the invitee once and never stored; only its hash
    is persisted so a database leak cannot yield working invite links.
    """

    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    role: Mapped[GlobalRole] = mapped_column(
        Enum(GlobalRole, name="global_role"), default=GlobalRole.member, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_pending(self) -> bool:
        from app.core.time import as_aware

        now = dt.datetime.now(dt.timezone.utc)
        expires = as_aware(self.expires_at)
        return (
            self.accepted_at is None
            and self.revoked_at is None
            and expires is not None
            and expires > now
        )
