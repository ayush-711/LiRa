from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import StatusCategory
from app.models.issue import Issue
from app.models.label import IssueLabel
from app.models.reference import IssuePriority, IssueStatus


# The set of columns eagerly loaded whenever we return issues for display.
def display_options():
    return (
        selectinload(Issue.type),
        selectinload(Issue.status),
        selectinload(Issue.priority),
        selectinload(Issue.assignee),
        selectinload(Issue.reporter),
        selectinload(Issue.project),
        selectinload(Issue.issue_labels).selectinload(IssueLabel.label),
    )


# Backwards-compatible alias used within this module.
_display_options = display_options


@dataclass
class IssueFilters:
    project_id: int | None = None
    assignee_ids: list[int] = field(default_factory=list)
    reporter_ids: list[int] = field(default_factory=list)
    status_ids: list[int] = field(default_factory=list)
    status_categories: list[StatusCategory] = field(default_factory=list)
    priority_ids: list[int] = field(default_factory=list)
    type_ids: list[int] = field(default_factory=list)
    label_ids: list[int] = field(default_factory=list)
    parent_id: int | None = None
    unassigned: bool = False
    overdue: bool = False
    due_before: dt.date | None = None
    search: str | None = None
    include_archived: bool = False
    include_subtasks: bool = True


_SORT_COLUMNS = {
    "created": Issue.created_at,
    "updated": Issue.updated_at,
    "due": Issue.due_date,
    "key": Issue.key,
    "title": Issue.title,
}


class IssueRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, issue_id: int) -> Issue | None:
        return await self.db.get(Issue, issue_id)

    async def get_display(self, issue_id: int) -> Issue | None:
        result = await self.db.execute(
            select(Issue).where(Issue.id == issue_id).options(*_display_options())
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> Issue | None:
        result = await self.db.execute(
            select(Issue).where(func.upper(Issue.key) == key.upper())
            .options(*_display_options())
        )
        return result.scalar_one_or_none()

    def _apply_filters(self, stmt, f: IssueFilters):
        conds = []
        if f.project_id is not None:
            conds.append(Issue.project_id == f.project_id)
        if not f.include_archived:
            conds.append(Issue.archived_at.is_(None))
        if f.assignee_ids:
            conds.append(Issue.assignee_id.in_(f.assignee_ids))
        if f.unassigned:
            conds.append(Issue.assignee_id.is_(None))
        if f.reporter_ids:
            conds.append(Issue.reporter_id.in_(f.reporter_ids))
        if f.status_ids:
            conds.append(Issue.status_id.in_(f.status_ids))
        if f.priority_ids:
            conds.append(Issue.priority_id.in_(f.priority_ids))
        if f.type_ids:
            conds.append(Issue.type_id.in_(f.type_ids))
        if f.parent_id is not None:
            conds.append(Issue.parent_id == f.parent_id)
        elif not f.include_subtasks:
            conds.append(Issue.parent_id.is_(None))
        if f.overdue:
            today = dt.date.today()
            conds.append(and_(Issue.due_date.is_not(None), Issue.due_date < today))
        if f.due_before is not None:
            conds.append(and_(Issue.due_date.is_not(None), Issue.due_date <= f.due_before))
        if f.status_categories:
            stmt = stmt.join(IssueStatus, Issue.status_id == IssueStatus.id)
            conds.append(IssueStatus.category.in_(f.status_categories))
        if f.label_ids:
            stmt = stmt.where(
                Issue.id.in_(
                    select(IssueLabel.issue_id).where(IssueLabel.label_id.in_(f.label_ids))
                )
            )
        if f.search:
            like = f"%{f.search.strip()}%"
            conds.append(
                or_(
                    Issue.title.ilike(like),
                    Issue.key.ilike(like),
                    cast(Issue.description, String).ilike(like),
                )
            )
        if conds:
            stmt = stmt.where(*conds)
        return stmt

    async def list(
        self,
        f: IssueFilters,
        *,
        sort: str = "updated",
        descending: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Issue]:
        stmt = select(Issue)
        stmt = self._apply_filters(stmt, f)
        col = _SORT_COLUMNS.get(sort, Issue.updated_at)
        stmt = stmt.order_by(col.desc() if descending else col.asc(), Issue.id.desc())
        stmt = stmt.options(*_display_options()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def count(self, f: IssueFilters) -> int:
        stmt = select(func.count(func.distinct(Issue.id)))
        stmt = self._apply_filters(stmt, f)
        return int((await self.db.execute(stmt)).scalar_one())

    async def board(self, project_id: int) -> list[Issue]:
        """All non-archived, top-level-and-sub issues for a project's board,
        ordered by board rank within each column."""
        stmt = (
            select(Issue)
            .where(Issue.project_id == project_id, Issue.archived_at.is_(None))
            .options(*_display_options())
            .order_by(Issue.board_rank.asc(), Issue.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def subtasks(self, parent_id: int) -> list[Issue]:
        stmt = (
            select(Issue)
            .where(Issue.parent_id == parent_id, Issue.archived_at.is_(None))
            .options(*_display_options())
            .order_by(Issue.number.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def max_board_rank(self, project_id: int, status_id: int) -> float:
        stmt = select(func.coalesce(func.max(Issue.board_rank), 0.0)).where(
            Issue.project_id == project_id, Issue.status_id == status_id
        )
        return float((await self.db.execute(stmt)).scalar_one())

    # Aggregations for dashboards
    async def count_by_status_category(
        self, project_id: int | None = None
    ) -> dict[str, int]:
        stmt = (
            select(IssueStatus.category, func.count(Issue.id))
            .join(IssueStatus, Issue.status_id == IssueStatus.id)
            .where(Issue.archived_at.is_(None))
            .group_by(IssueStatus.category)
        )
        if project_id is not None:
            stmt = stmt.where(Issue.project_id == project_id)
        rows = (await self.db.execute(stmt)).all()
        return {cat.value: n for cat, n in rows}

    def add(self, issue: Issue) -> None:
        self.db.add(issue)
