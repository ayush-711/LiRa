from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.comment import Comment
    from app.models.label import IssueLabel
    from app.models.project import Project
    from app.models.reference import IssuePriority, IssueStatus, IssueType
    from app.models.user import User


class Issue(Base, TimestampMixin):
    __tablename__ = "issues"
    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_issue_project_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Per-project sequence number; combined with project.key gives the human key.
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    key: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    type_id: Mapped[int] = mapped_column(
        ForeignKey("issue_types.id"), index=True, nullable=False
    )
    status_id: Mapped[int] = mapped_column(
        ForeignKey("issue_statuses.id"), index=True, nullable=False
    )
    priority_id: Mapped[int] = mapped_column(
        ForeignKey("issue_priorities.id"), index=True, nullable=False
    )

    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    reporter_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("issues.id", ondelete="SET NULL"), index=True, nullable=True
    )

    due_date: Mapped[dt.date | None] = mapped_column(Date, index=True, nullable=True)

    # Optional effort estimate in points. Enables throughput/velocity reporting
    # without imposing a sprint process.
    estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Last date a due-date reminder was sent, so the daily job never double-sends.
    last_due_reminder_on: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    # Ordering within a board column (fractional/float for cheap reordering).
    board_rank: Mapped[float] = mapped_column(default=0.0, nullable=False)

    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ──────────────────────────────────────────
    project: Mapped["Project"] = relationship(back_populates="issues")
    type: Mapped["IssueType"] = relationship()
    status: Mapped["IssueStatus"] = relationship()
    priority: Mapped["IssuePriority"] = relationship()
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])
    reporter: Mapped["User | None"] = relationship(foreign_keys=[reporter_id])
    parent: Mapped["Issue | None"] = relationship(remote_side=[id], foreign_keys=[parent_id])

    issue_labels: Mapped[list["IssueLabel"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None
