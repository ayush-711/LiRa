from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class ActivityEvent(Base, TimestampMixin):
    """User-facing, immutable issue/project history entry.

    Rendered into human-readable sentences in the UI from structured fields.
    Distinct from AuditLog (security/admin trail).
    """

    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int | None] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), index=True, nullable=True
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True
    )
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # e.g. "issue.created", "issue.status_changed", "issue.assigned", "comment.added"
    event_type: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    field: Mapped[str | None] = mapped_column(String(60), nullable=True)
    old_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    actor: Mapped["User | None"] = relationship()
