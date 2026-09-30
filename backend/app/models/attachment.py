from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.user import User


class Attachment(Base, TimestampMixin):
    """File attachment metadata. Binary content lives on disk under UPLOAD_ROOT,
    never in the database. ``storage_path`` is relative to UPLOAD_ROOT.
    """

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    issue: Mapped["Issue"] = relationship(back_populates="attachments")
    uploaded_by: Mapped["User | None"] = relationship()
