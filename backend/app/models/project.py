from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ProjectStatus

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.project_member import ProjectMember


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        default=ProjectStatus.active,
        nullable=False,
    )
    # Optional coarse priority label for the project itself.
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)

    start_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    target_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Monotonic per-project issue counter; DOC-1, DOC-2, ... Updated under row lock.
    issue_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Must be timezone-aware to match every other timestamp; without the
    # explicit type this became TIMESTAMP WITHOUT TIME ZONE and Postgres
    # rejected the aware datetime the service writes.
    archived_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    issues: Mapped[list["Issue"]] = relationship(back_populates="project")

    @property
    def is_archived(self) -> bool:
        return self.status == ProjectStatus.archived
