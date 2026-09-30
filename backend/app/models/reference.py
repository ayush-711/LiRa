"""Reference/lookup tables: issue statuses, types, priorities.

Stored as rows (not code enums) so the workflow can be extended later. Seeded on
startup by app.scripts.seed_reference. Statuses carry a ``category`` for
consistent counting and an ``order_index`` for board column ordering.
"""
from __future__ import annotations

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import StatusCategory


class IssueStatus(Base, TimestampMixin):
    __tablename__ = "issue_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    category: Mapped[StatusCategory] = mapped_column(
        Enum(StatusCategory, name="status_category"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#94a3b8", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Optional project association reserved for future per-project workflows.
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )


class IssueType(Base, TimestampMixin):
    __tablename__ = "issue_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    icon: Mapped[str] = mapped_column(String(40), default="circle", nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#64748b", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class IssuePriority(Base, TimestampMixin):
    __tablename__ = "issue_priorities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    # Higher rank = more urgent (Urgent=4 ... None=0). Used for sorting.
    rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#94a3b8", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
