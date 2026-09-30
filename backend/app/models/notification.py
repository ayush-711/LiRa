from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Notification(Base, TimestampMixin):
    """In-app notification for a user. Email is a parallel channel, not this row."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # e.g. "issue_assigned", "mention", "comment", "due_soon", "status_changed"
    type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    issue_id: Mapped[int | None] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), nullable=True
    )
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    read_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    actor: Mapped["User | None"] = relationship(foreign_keys=[actor_id])


class NotificationPreference(Base, TimestampMixin):
    """Per-user notification channel preferences (extensible)."""

    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    email_on_assignment: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_on_mention: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_on_comment: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_on_due_reminder: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_on_status_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
