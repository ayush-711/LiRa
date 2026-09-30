from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base, TimestampMixin):
    """Organisation-level security/administrative audit trail.

    Append-only: never edited or deleted through the application. Distinct from
    the user-facing ActivityEvent feed.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # e.g. "login", "login_failed", "invitation.created", "user.deactivated",
    # "role.changed", "project.created", "project.archived", "issue.deleted"
    action: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(400), nullable=True)

    actor: Mapped["User | None"] = relationship()
