from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class SavedView(Base, TimestampMixin):
    """A named, reusable set of issue filters ("my slice of work").

    ``filters`` stores the same query parameters the issue list accepts, so a
    view is just a saved query — no special-casing in the list endpoint.
    A view scoped to a project shows up on that project; a global view (no
    project_id) shows everywhere.
    """

    __tablename__ = "saved_views"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True
    )
    filters: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    # Shared views are visible to the whole team (read-only for non-owners).
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    owner: Mapped["User"] = relationship()
