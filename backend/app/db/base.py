"""Declarative base and shared column/type helpers for ORM models."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Portable JSON: JSONB on PostgreSQL, plain JSON elsewhere (e.g. SQLite in tests).
JSONType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class TimestampMixin:
    """Adds created_at / updated_at columns (UTC, DB-managed)."""

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
