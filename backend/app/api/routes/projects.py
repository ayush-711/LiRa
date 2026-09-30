from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.issue_repo import IssueFilters, IssueRepository
from app.repositories.misc_repos import ActivityRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.reference_repo import ReferenceRepository
from app.api.serializers import activity_to_out, issue_to_summary
from app.models.enums import StatusCategory
from app.schemas.common import MessageResponse
from app.schemas.issue import IssueSummary
from app.schemas.misc import ActivityOut
from app.schemas.project import (
    MemberAdd,
    ProjectCreate,
    ProjectMemberOut,
    ProjectOut,
    ProjectStats,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


async def _to_out(db, project, user) -> ProjectOut:
    role = await ProjectRepository(db).member_role(project.id, user.id)
    out = ProjectOut.model_validate(project)
    out.my_role = role
    return out


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    include_archived: bool = False,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[ProjectOut]:
    projects = await ProjectRepository(db).list(include_archived=include_archived)
    return [await _to_out(db, p, user) for p in projects]


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    payload: ProjectCreate, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ProjectOut:
    project = await ProjectService(db).create(
        actor=user, name=payload.name, key=payload.key, description=payload.description,
        lead_id=payload.lead_id, priority=payload.priority,
        start_date=payload.start_date, target_date=payload.target_date, request=request,
    )
    return await _to_out(db, project, user)


@router.get("/{key}", response_model=ProjectOut)
async def get_project(
    key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ProjectOut:
    project = await ProjectService(db).get_by_key_or_404(key)
    return await _to_out(db, project, user)


@router.patch("/{key}", response_model=ProjectOut)
async def update_project(
    key: str, payload: ProjectUpdate, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ProjectOut:
    service = ProjectService(db)
    project = await service.get_by_key_or_404(key)
    role = await ProjectRepository(db).member_role(project.id, user.id)
    project = await service.update(
        project, actor=user, member_role=role,
        changes=payload.model_dump(exclude_unset=True), request=request,
    )
    return await _to_out(db, project, user)


@router.post("/{key}/archive", response_model=ProjectOut)
async def archive_project(
    key: str, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ProjectOut:
    service = ProjectService(db)
    project = await service.get_by_key_or_404(key)
    role = await ProjectRepository(db).member_role(project.id, user.id)
    project = await service.archive(project, actor=user, member_role=role, request=request)
    return await _to_out(db, project, user)


@router.post("/{key}/unarchive", response_model=ProjectOut)
async def unarchive_project(
    key: str, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ProjectOut:
    service = ProjectService(db)
    project = await service.get_by_key_or_404(key)
    role = await ProjectRepository(db).member_role(project.id, user.id)
    project = await service.unarchive(project, actor=user, member_role=role, request=request)
    return await _to_out(db, project, user)


@router.get("/{key}/stats", response_model=ProjectStats)
async def project_stats(
    key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ProjectStats:
    project = await ProjectService(db).get_by_key_or_404(key)
    issues = IssueRepository(db)
    ref = ReferenceRepository(db)
    counts = await issues.count_by_status_category(project.id)
    done = counts.get(StatusCategory.done.value, 0)
    total = sum(counts.values())
    in_progress = counts.get(StatusCategory.in_progress.value, 0)
    overdue = await issues.count(IssueFilters(project_id=project.id, overdue=True))
    urgent_ids = [p.id for p in await ref.priorities() if p.rank >= 4]
    urgent = await issues.count(IssueFilters(project_id=project.id, priority_ids=urgent_ids))
    return ProjectStats(
        total_issues=total, open_issues=total - done, in_progress=in_progress,
        done=done, overdue=overdue, urgent=urgent,
        completion=round(done / total * 100) if total else 0,
    )


# ── Members ────────────────────────────────────────────────────
@router.get("/{key}/members", response_model=list[ProjectMemberOut])
async def list_members(
    key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[ProjectMemberOut]:
    project = await ProjectService(db).get_by_key_or_404(key)
    members = await ProjectRepository(db).list_members(project.id)
    return [ProjectMemberOut.model_validate(m) for m in members]


@router.post("/{key}/members", response_model=ProjectMemberOut, status_code=201)
async def add_member(
    key: str, payload: MemberAdd, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ProjectMemberOut:
    service = ProjectService(db)
    project = await service.get_by_key_or_404(key)
    actor_role = await ProjectRepository(db).member_role(project.id, user.id)
    member = await service.add_member(
        project, user_id=payload.user_id, role=payload.role,
        actor=user, actor_role=actor_role, request=request,
    )
    await db.refresh(member, attribute_names=["user"])
    return ProjectMemberOut.model_validate(member)


@router.patch("/{key}/members/{user_id}", response_model=ProjectMemberOut)
async def update_member_role(
    key: str, user_id: int, payload: MemberAdd, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> ProjectMemberOut:
    """Promote/demote a project member (manager ↔ member)."""
    from app.auth import permissions
    from app.core.errors import NotFoundError, PermissionDeniedError

    service = ProjectService(db)
    project = await service.get_by_key_or_404(key)
    repo = ProjectRepository(db)
    actor_role = await repo.member_role(project.id, user.id)
    if not permissions.can_manage_project(user, actor_role):
        raise PermissionDeniedError("You cannot manage this project's members")

    membership = await repo.get_membership(project.id, user_id)
    if membership is None:
        raise NotFoundError("Membership not found", code="MEMBERSHIP_NOT_FOUND")
    membership.role = payload.role
    await db.commit()
    await db.refresh(membership, attribute_names=["user"])
    return ProjectMemberOut.model_validate(membership)


@router.delete("/{key}/members/{user_id}", response_model=MessageResponse)
async def remove_member(
    key: str, user_id: int, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    service = ProjectService(db)
    project = await service.get_by_key_or_404(key)
    actor_role = await ProjectRepository(db).member_role(project.id, user.id)
    await service.remove_member(
        project, user_id=user_id, actor=user, actor_role=actor_role, request=request
    )
    return MessageResponse(message="Member removed")


# ── Activity ───────────────────────────────────────────────────
@router.get("/{key}/activity", response_model=list[ActivityOut])
async def project_activity(
    key: str, limit: int = 50, offset: int = 0,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[ActivityOut]:
    project = await ProjectService(db).get_by_key_or_404(key)
    events = await ActivityRepository(db).for_project(project.id, limit=limit, offset=offset)
    return [activity_to_out(e) for e in events]
