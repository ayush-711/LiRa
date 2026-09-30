from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.user import User


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    edited_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    issue: Mapped["Issue"] = relationship(back_populates="comments")
    author: Mapped["User | None"] = relationship()
