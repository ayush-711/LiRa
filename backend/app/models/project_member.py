from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ProjectRole

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ProjectMember(Base, TimestampMixin):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[ProjectRole] = mapped_column(
        Enum(ProjectRole, name="project_role"), default=ProjectRole.member, nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")
