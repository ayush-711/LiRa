from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import issue_to_summary
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.issue_repo import IssueFilters, IssueRepository
from app.repositories.reference_repo import ReferenceRepository
from app.schemas.issue import BoardColumn, BoardOut
from app.schemas.meta import StatusOut
from app.services.issue_rules import is_overdue
from app.services.project_service import ProjectService

router = APIRouter(tags=["views"])


@router.get("/projects/{key}/board", response_model=BoardOut)
async def project_board(
    key: str,
    assignee: int | None = None,
    priority: int | None = None,
    type: int | None = None,
    label: int | None = None,
    mine: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BoardOut:
    project = await ProjectService(db).get_by_key_or_404(key)
    statuses = await ReferenceRepository(db).statuses()
    issues = await IssueRepository(db).board(project.id)

    # Optional composable filters applied in-memory (board is small per project).
    def _keep(i) -> bool:
        if mine and i.assignee_id != user.id:
            return False
        if assignee and i.assignee_id != assignee:
            return False
        if priority and i.priority_id != priority:
            return False
        if type and i.type_id != type:
            return False
        if label and not any(il.label_id == label for il in i.issue_labels):
            return False
        return True

    by_status: dict[int, list] = {s.id: [] for s in statuses}
    for issue in issues:
        if issue.status_id in by_status and _keep(issue):
            by_status[issue.status_id].append(issue)

    columns = [
        BoardColumn(
            status=StatusOut.model_validate(s),
            issues=[issue_to_summary(i) for i in by_status[s.id]],
        )
        for s in statuses
    ]
    return BoardOut(columns=columns)


@router.get("/my-issues", response_model=dict)
async def my_issues(
    sort: str = Query("priority", pattern="^(priority|due|updated|project|status)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Issues assigned to the current user, grouped by workflow status.

    Groups mirror the real workflow (Backlog → Todo → In Progress → Resolved →
    Ready for QA → Done) rather than invented buckets, so the sections here match
    the board columns exactly. Empty statuses are omitted.
    """
    repo = IssueRepository(db)
    ref = ReferenceRepository(db)

    f = IssueFilters(assignee_ids=[user.id])
    sort_map = {"priority": "updated", "due": "due", "updated": "updated",
                "project": "key", "status": "updated"}
    rows = await repo.list(f, sort=sort_map.get(sort, "updated"), limit=200)

    statuses = await ref.statuses()
    priorities = {p.id: p.rank for p in await ref.priorities()}

    by_status: dict[int, list] = {s.id: [] for s in statuses}
    for i in rows:
        if i.status_id in by_status:
            by_status[i.status_id].append(i)

    # Within a group, surface the most pressing work first: overdue, then
    # priority, then nearest due date.
    def order_key(i):
        return (
            0 if is_overdue(i) else 1,
            -priorities.get(i.priority_id, 0),
            i.due_date or dt.date.max,
        )

    groups = []
    for s in statuses:
        items = by_status.get(s.id, [])
        if not items:
            continue
        if sort == "priority":
            items = sorted(items, key=order_key)
        elif sort == "due":
            items = sorted(items, key=lambda i: i.due_date or dt.date.max)
        groups.append({
            "status": StatusOut.model_validate(s).model_dump(),
            "issues": [issue_to_summary(i).model_dump() for i in items],
        })

    return {"groups": groups, "total": len(rows)}
