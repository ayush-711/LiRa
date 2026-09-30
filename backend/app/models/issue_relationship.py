from __future__ import annotations

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import RelationshipType


class IssueRelationship(Base, TimestampMixin):
    """A directed link between two issues.

    `blocks`: source_issue blocks target_issue (rendered as "blocked by" on target).
    `relates_to`: symmetric; stored once, shown on both sides.
    Parent/subtask is modelled separately via issues.parent_id.
    """

    __tablename__ = "issue_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_issue_id", "target_issue_id", "type", name="uq_issue_relationship"
        ),
        CheckConstraint(
            "source_issue_id <> target_issue_id", name="ck_relationship_no_self"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[RelationshipType] = mapped_column(
        Enum(RelationshipType, name="relationship_type"), nullable=False
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
