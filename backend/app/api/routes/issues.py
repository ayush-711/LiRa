from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import activity_to_out, issue_to_detail, issue_to_summary
from app.core.deps import get_current_user, get_db
from app.core.errors import AppError, ValidationError
from app.repositories.label_repo import LabelRepository
from app.models.enums import RelationshipType
from app.models.user import User
from app.repositories.comment_repo import CommentRepository
from app.repositories.issue_repo import IssueFilters, IssueRepository
from app.repositories.misc_repos import (
    ActivityRepository,
    AttachmentRepository,
    RelationshipRepository,
)
from app.repositories.reference_repo import ReferenceRepository
from app.schemas.common import MessageResponse, Page
from app.schemas.issue import (
    BulkResult,
    BulkUpdate,
    IssueCreate,
    IssueDetail,
    IssueMove,
    IssueSummary,
    IssueUpdate,
    RelatedIssue,
    RelationshipCreate,
)
from app.schemas.misc import (
    ActivityOut,
    AttachmentOut,
    CommentCreate,
    CommentOut,
)
from app.services.attachment_service import AttachmentService
from app.services.comment_service import CommentService
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.relationship_service import RelationshipService

router = APIRouter(tags=["issues"])


def _csv_ints(value: str | None) -> list[int]:
    if not value:
        return []
    out = []
    for part in value.split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


async def _detail(db: AsyncSession, issue) -> IssueDetail:
    issues = IssueRepository(db)
    comments = CommentRepository(db)
    attachments = AttachmentRepository(db)
    subtasks = await issues.subtasks(issue.id)
    from app.models.enums import StatusCategory
    done = sum(1 for s in subtasks if s.status and s.status.category == StatusCategory.done)
    return issue_to_detail(
        issue,
        subtask_total=len(subtasks),
        subtask_done=done,
        comment_count=await comments.count_for_issue(issue.id),
        attachment_count=len(await attachments.list_for_issue(issue.id)),
    )


# ── Listing / filtering ────────────────────────────────────────
@router.get("/issues", response_model=Page[IssueSummary])
async def list_issues(
    request: Request,
    project: str | None = None,
    assignee: str | None = None,
    reporter: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    type: str | None = None,
    label: str | None = None,
    parent_id: int | None = None,
    mine: bool = False,
    unassigned: bool = False,
    overdue: bool = False,
    due_before: dt.date | None = None,
    search: str | None = None,
    include_archived: bool = False,
    include_subtasks: bool = True,
    sort: str = Query("updated", pattern="^(updated|created|due|key|title)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page[IssueSummary]:
    project_id = None
    if project:
        project_id = (await ProjectService(db).get_by_key_or_404(project)).id

    assignee_ids = _csv_ints(assignee)
    if mine:
        assignee_ids = list(set(assignee_ids) | {user.id})

    f = IssueFilters(
        project_id=project_id,
        assignee_ids=assignee_ids,
        reporter_ids=_csv_ints(reporter),
        status_ids=_csv_ints(status),
        priority_ids=_csv_ints(priority),
        type_ids=_csv_ints(type),
        label_ids=_csv_ints(label),
        parent_id=parent_id,
        unassigned=unassigned,
        overdue=overdue,
        due_before=due_before,
        search=search,
        include_archived=include_archived,
        include_subtasks=include_subtasks,
    )
    repo = IssueRepository(db)
    total = await repo.count(f)
    rows = await repo.list(f, sort=sort, descending=(order == "desc"), limit=limit, offset=offset)
    return Page(items=[issue_to_summary(i) for i in rows], total=total, limit=limit, offset=offset)


@router.post("/issues", response_model=IssueDetail, status_code=201)
async def create_issue(
    payload: IssueCreate, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> IssueDetail:
    if payload.project_id is None:
        raise ValidationError("project_id is required", code="PROJECT_REQUIRED")
    project = await ProjectService(db).get_or_404(payload.project_id)
    issue = await IssueService(db).create(
        actor=user, project=project, title=payload.title, description=payload.description,
        type_id=payload.type_id, status_id=payload.status_id, priority_id=payload.priority_id,
        assignee_id=payload.assignee_id, due_date=payload.due_date,
        estimate=payload.estimate, parent_id=payload.parent_id,
        label_ids=payload.label_ids, request=request,
    )
    return await _detail(db, issue)


@router.post("/issues/bulk", response_model=BulkResult)
async def bulk_update_issues(
    payload: BulkUpdate, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> BulkResult:
    """Apply one change across many issues.

    Authorization, activity and audit run per issue via the normal service path;
    a failure on one issue is reported and does not abort the rest.
    """
    service = IssueService(db)
    updated = 0
    failed: list[dict] = []

    for key in payload.keys:
        try:
            issue = await service.get_by_key_or_404(key)
            if payload.archive:
                await service.archive(issue, actor=user, request=request)
                updated += 1
                continue

            changes: dict = {}
            for field in ("status_id", "priority_id"):
                if getattr(payload, field) is not None:
                    changes[field] = getattr(payload, field)
            if payload.assignee_id is not None:
                changes["assignee_id"] = payload.assignee_id

            if payload.add_label_ids or payload.remove_label_ids:
                current = {l.label_id for l in await LabelRepository(db).links_for_issue(issue.id)}
                current |= set(payload.add_label_ids or [])
                current -= set(payload.remove_label_ids or [])
                changes["label_ids"] = sorted(current)

            if not changes:
                continue
            await service.update(issue, actor=user, changes=changes, request=request)
            updated += 1
        except AppError as exc:
            failed.append({"key": key, "error": exc.message})
        except Exception:
            failed.append({"key": key, "error": "Unexpected error"})

    return BulkResult(updated=updated, failed=failed)


@router.get("/issues/{key}", response_model=IssueDetail)
async def get_issue(
    key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> IssueDetail:
    issue = await IssueService(db).get_by_key_or_404(key)
    return await _detail(db, issue)


@router.patch("/issues/{key}", response_model=IssueDetail)
async def update_issue(
    key: str, payload: IssueUpdate, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> IssueDetail:
    service = IssueService(db)
    issue = await service.get_by_key_or_404(key)
    issue = await service.update(
        issue, actor=user, changes=payload.model_dump(exclude_unset=True), request=request
    )
    return await _detail(db, issue)


@router.post("/issues/{key}/move", response_model=IssueDetail)
async def move_issue(
    key: str, payload: IssueMove, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> IssueDetail:
    service = IssueService(db)
    issue = await service.get_by_key_or_404(key)
    issue = await service.move(
        issue, actor=user, status_id=payload.status_id, rank=payload.rank, request=request
    )
    return await _detail(db, issue)


@router.post("/issues/{key}/archive", response_model=IssueDetail)
async def archive_issue(
    key: str, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> IssueDetail:
    service = IssueService(db)
    issue = await service.get_by_key_or_404(key)
    issue = await service.archive(issue, actor=user, request=request)
    return await _detail(db, issue)


@router.get("/issues/{key}/subtasks", response_model=list[IssueSummary])
async def list_subtasks(
    key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[IssueSummary]:
    issue = await IssueService(db).get_by_key_or_404(key)
    rows = await IssueRepository(db).subtasks(issue.id)
    return [issue_to_summary(i) for i in rows]


# ── Comments ───────────────────────────────────────────────────
@router.get("/issues/{key}/comments", response_model=list[CommentOut])
async def list_comments(
    key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[CommentOut]:
    issue = await IssueService(db).get_by_key_or_404(key)
    rows = await CommentService(db).list_for_issue(issue.id)
    return [CommentOut.model_validate(c) for c in rows]


@router.post("/issues/{key}/comments", response_model=CommentOut, status_code=201)
async def add_comment(
    key: str, payload: CommentCreate, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> CommentOut:
    issue = await IssueService(db).get_by_key_or_404(key)
    comment = await CommentService(db).create(
        issue_id=issue.id, actor=user, body=payload.body, request=request
    )
    await db.refresh(comment, attribute_names=["author"])
    return CommentOut.model_validate(comment)


@router.patch("/comments/{comment_id}", response_model=CommentOut)
async def edit_comment(
    comment_id: int, payload: CommentCreate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> CommentOut:
    comment = await CommentService(db).update(comment_id, actor=user, body=payload.body)
    await db.refresh(comment, attribute_names=["author"])
    return CommentOut.model_validate(comment)


@router.delete("/comments/{comment_id}", response_model=MessageResponse)
async def delete_comment(
    comment_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await CommentService(db).delete(comment_id, actor=user)
    return MessageResponse(message="Comment deleted")


# ── Activity ───────────────────────────────────────────────────
@router.get("/issues/{key}/activity", response_model=list[ActivityOut])
async def issue_activity(
    key: str, limit: int = 100, offset: int = 0,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[ActivityOut]:
    issue = await IssueService(db).get_by_key_or_404(key)
    events = await ActivityRepository(db).for_issue(issue.id, limit=limit, offset=offset)
    return [activity_to_out(e) for e in events]


# ── Relationships ──────────────────────────────────────────────
@router.get("/issues/{key}/relationships", response_model=list[RelatedIssue])
async def list_relationships(
    key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[RelatedIssue]:
    issue = await IssueService(db).get_by_key_or_404(key)
    rels = await RelationshipService(db).list_for_issue(issue.id)
    issues_repo = IssueRepository(db)
    out: list[RelatedIssue] = []
    for rel in rels:
        outgoing = rel.source_issue_id == issue.id
        other_id = rel.target_issue_id if outgoing else rel.source_issue_id
        other = await issues_repo.get_display(other_id)
        if other is None:
            continue
        out.append(RelatedIssue(
            relationship_id=rel.id, type=rel.type,
            direction="outgoing" if outgoing else "incoming",
            issue=issue_to_summary(other),
        ))
    return out


@router.post("/issues/{key}/relationships", response_model=RelatedIssue, status_code=201)
async def add_relationship(
    key: str, payload: RelationshipCreate, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> RelatedIssue:
    service = IssueService(db)
    issue = await service.get_by_key_or_404(key)
    rel = await RelationshipService(db).create(
        source_id=issue.id, target_key=payload.target_key, type=payload.type,
        actor=user, request=request,
    )
    other = await IssueRepository(db).get_display(rel.target_issue_id)
    return RelatedIssue(
        relationship_id=rel.id, type=rel.type, direction="outgoing",
        issue=issue_to_summary(other),
    )


@router.delete("/relationships/{rel_id}", response_model=MessageResponse)
async def delete_relationship(
    rel_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await RelationshipService(db).delete(rel_id, actor=user)
    return MessageResponse(message="Relationship removed")


# ── Attachments ────────────────────────────────────────────────
@router.get("/issues/{key}/attachments", response_model=list[AttachmentOut])
async def list_attachments(
    key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[AttachmentOut]:
    issue = await IssueService(db).get_by_key_or_404(key)
    rows = await AttachmentService(db).list_for_issue(issue.id)
    return [AttachmentOut.model_validate(a) for a in rows]


@router.post("/issues/{key}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    key: str, request: Request, file: UploadFile,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> AttachmentOut:
    issue = await IssueService(db).get_by_key_or_404(key)
    attachment = await AttachmentService(db).upload(
        issue_id=issue.id, actor=user, upload=file, request=request
    )
    await db.refresh(attachment, attribute_names=["uploaded_by"])
    return AttachmentOut.model_validate(attachment)
