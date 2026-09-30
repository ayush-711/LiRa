"""Centralised issue business rules (single source of truth).

Overdue: due_date < today AND status is not in the `done` category AND not archived.
"""
from __future__ import annotations

import datetime as dt

from app.models.enums import StatusCategory
from app.models.issue import Issue


def is_overdue(issue: Issue, *, today: dt.date | None = None) -> bool:
    if issue.due_date is None or issue.archived_at is not None:
        return False
    today = today or dt.date.today()
    if issue.status and issue.status.category == StatusCategory.done:
        return False
    return issue.due_date < today
