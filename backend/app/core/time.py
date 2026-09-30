"""Timezone helpers.

Postgres returns timezone-aware datetimes for ``TIMESTAMPTZ`` columns; SQLite
(used in tests) returns naive ones. These helpers keep comparisons correct on
both by treating naive values as UTC.
"""
from __future__ import annotations

import datetime as dt


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def as_aware(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value
