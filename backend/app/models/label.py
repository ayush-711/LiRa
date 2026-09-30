from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.issue import Issue


class Label(Base, TimestampMixin):
    """Global labels (V1). A project_id column is reserved for future scoping."""

    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#6366f1", nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class IssueLabel(Base):
    """Association between issues and labels."""

    __tablename__ = "issue_labels"
    __table_args__ = (
        UniqueConstraint("issue_id", "label_id", name="uq_issue_label"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label_id: Mapped[int] = mapped_column(
        ForeignKey("labels.id", ondelete="CASCADE"), index=True, nullable=False
    )

    label: Mapped["Label"] = relationship()
    issue: Mapped["Issue"] = relationship(back_populates="issue_labels")
