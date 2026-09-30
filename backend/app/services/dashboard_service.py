"""Operational dashboard aggregations.

Counting semantics (documented, applied consistently):
  open      = not Done and not archived
  completed = Done category
  overdue   = due_date < today and not Done and not archived
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStatus, StatusCategory
from app.models.issue import Issue
from app.models.project import Project
from app.models.reference import IssuePriority, IssueStatus
from app.repositories.issue_repo import IssueFilters, IssueRepository


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.issues = IssueRepository(db)

    async def _count(self, *conds) -> int:
        stmt = select(func.count(Issue.id)).where(Issue.archived_at.is_(None), *conds)
        return int((await self.db.execute(stmt)).scalar_one())

    async def _open_cond(self):
        done = await self._done_status_ids()
        return Issue.status_id.notin_(done) if done else True

    async def _done_status_ids(self) -> list[int]:
        rows = (
            await self.db.execute(
                select(IssueStatus.id).where(IssueStatus.category == StatusCategory.done)
            )
        ).all()
        return [r[0] for r in rows]

    async def _urgent_priority_ids(self) -> list[int]:
        rows = (
            await self.db.execute(
                select(IssuePriority.id).where(IssuePriority.rank >= 4)
            )
        ).all()
        return [r[0] for r in rows]

    async def overview(self) -> dict:
        done_ids = await self._done_status_ids()
        urgent_ids = await self._urgent_priority_ids()
        today = dt.date.today()
        week_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)

        open_cond = Issue.status_id.notin_(done_ids) if done_ids else True
        active_projects = int(
            (await self.db.execute(
                select(func.count(Project.id)).where(Project.status == ProjectStatus.active)
            )).scalar_one()
        )
        return {
            "active_projects": active_projects,
            "open_issues": await self._count(open_cond),
            "overdue_issues": await self._count(
                open_cond, Issue.due_date.is_not(None), Issue.due_date < today
            ),
            "urgent_issues": await self._count(
                open_cond, Issue.priority_id.in_(urgent_ids) if urgent_ids else False
            ),
            "completed_recently": await self._count(
                Issue.completed_at.is_not(None), Issue.completed_at >= week_ago
            ),
        }

    async def personal(self, user_id: int) -> dict:
        done_ids = await self._done_status_ids()
        urgent_ids = await self._urgent_priority_ids()
        today = dt.date.today()
        soon = today + dt.timedelta(days=7)
        open_cond = Issue.status_id.notin_(done_ids) if done_ids else True
        mine = Issue.assignee_id == user_id
        return {
            "my_open": await self._count(mine, open_cond),
            "my_overdue": await self._count(
                mine, open_cond, Issue.due_date.is_not(None), Issue.due_date < today
            ),
            "my_urgent": await self._count(
                mine, open_cond, Issue.priority_id.in_(urgent_ids) if urgent_ids else False
            ),
            "my_upcoming": await self._count(
                mine, open_cond, Issue.due_date.is_not(None),
                and_(Issue.due_date >= today, Issue.due_date <= soon),
            ),
        }

    async def issues_by_status(self) -> list[dict]:
        rows = (
            await self.db.execute(
                select(IssueStatus.id, IssueStatus.name, IssueStatus.color,
                       func.count(Issue.id))
                .join(Issue, and_(Issue.status_id == IssueStatus.id, Issue.archived_at.is_(None)),
                      isouter=True)
                .group_by(IssueStatus.id)
                .order_by(IssueStatus.order_index)
            )
        ).all()
        return [
            {"id": sid, "name": n, "color": c, "count": cnt}
            for sid, n, c, cnt in rows
        ]

    async def project_summaries(self) -> list[dict]:
        """Per-project totals in two queries regardless of project count.

        (Previously this ran two COUNTs per project — an N+1 that grew with the
        number of projects.)
        """
        done_ids = await self._done_status_ids()
        projects = (
            await self.db.execute(
                select(Project).where(Project.status != ProjectStatus.archived)
                .order_by(Project.name)
            )
        ).scalars().all()

        # One grouped query for totals, one for completed.
        totals = dict(
            (
                await self.db.execute(
                    select(Issue.project_id, func.count(Issue.id))
                    .where(Issue.archived_at.is_(None))
                    .group_by(Issue.project_id)
                )
            ).all()
        )
        done_counts: dict[int, int] = {}
        if done_ids:
            done_counts = dict(
                (
                    await self.db.execute(
                        select(Issue.project_id, func.count(Issue.id))
                        .where(
                            Issue.archived_at.is_(None),
                            Issue.status_id.in_(done_ids),
                        )
                        .group_by(Issue.project_id)
                    )
                ).all()
            )

        # Most recent issue update per project — drives "most active first".
        last_activity = dict(
            (
                await self.db.execute(
                    select(Issue.project_id, func.max(Issue.updated_at))
                    .where(Issue.archived_at.is_(None))
                    .group_by(Issue.project_id)
                )
            ).all()
        )

        out = []
        for p in projects:
            total = totals.get(p.id, 0)
            done = done_counts.get(p.id, 0)
            out.append({
                "id": p.id, "key": p.key, "name": p.name, "status": p.status.value,
                "total_issues": total, "done_issues": done,
                "completion": round(done / total * 100) if total else 0,
                "last_activity_at": (
                    last_activity[p.id].isoformat() if last_activity.get(p.id) else None
                ),
            })

        # Busiest/most recently touched projects first so the dashboard's
        # top-5 slice shows what the team is actually working on.
        out.sort(
            key=lambda p: (p["last_activity_at"] or "", p["total_issues"]),
            reverse=True,
        )
        return out

    async def throughput(self, weeks: int = 8) -> list[dict]:
        """Issues completed per week for the last `weeks` weeks.

        A process-neutral delivery signal: it needs no sprints or cycles, just
        completion timestamps. Estimates are summed too when present.
        """
        start = dt.datetime.now(dt.timezone.utc) - dt.timedelta(weeks=weeks)
        rows = (
            await self.db.execute(
                select(Issue.completed_at, Issue.estimate).where(
                    Issue.completed_at.is_not(None),
                    Issue.completed_at >= start,
                    Issue.archived_at.is_(None),
                )
            )
        ).all()

        buckets: dict[str, dict] = {}
        today = dt.date.today()
        # Pre-seed the buckets so empty weeks still render.
        for i in range(weeks - 1, -1, -1):
            monday = today - dt.timedelta(days=today.weekday() + 7 * i)
            buckets[monday.isoformat()] = {"week": monday.isoformat(), "count": 0, "points": 0}

        for completed_at, estimate in rows:
            d = completed_at.date() if hasattr(completed_at, "date") else completed_at
            monday = d - dt.timedelta(days=d.weekday())
            b = buckets.get(monday.isoformat())
            if b is not None:
                b["count"] += 1
                b["points"] += estimate or 0

        return list(buckets.values())
