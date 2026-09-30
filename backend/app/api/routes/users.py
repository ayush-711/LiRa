from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_admin
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.misc import NotificationPreferencesOut, NotificationPreferencesUpdate
from app.schemas.user import (
    PasswordChange,
    ProfileUpdate,
    UserPublic,
    UserUpdateRole,
    UserWithStats,
)
from app.repositories.misc_repos import NotificationRepository
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService

router = APIRouter(tags=["users"])


@router.get("/users", response_model=list[UserWithStats])
async def list_users(
    _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[UserWithStats]:
    """Team page: all users with workload stats (read-only for non-admins)."""
    users = await UserRepository(db).list()
    stats = await UserService(db).workload_stats()
    out = []
    for u in users:
        s = stats.get(u.id, {})
        out.append(UserWithStats(
            **UserPublic.model_validate(u).model_dump(),
            assigned=s.get("assigned", 0),
            in_progress=s.get("in_progress", 0),
            overdue=s.get("overdue", 0),
            last_login_at=u.last_login_at,
        ))
    return out


@router.get("/users/{user_id}/projects", response_model=list[dict])
async def user_projects(
    user_id: int, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Which projects a user belongs to, and with what role.

    Powers the per-person project-access controls on the Team page.
    """
    from sqlalchemy import select

    from app.models.project import Project
    from app.models.project_member import ProjectMember

    rows = (
        await db.execute(
            select(ProjectMember, Project)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(ProjectMember.user_id == user_id)
            .order_by(Project.name)
        )
    ).all()
    return [
        {
            "project_id": p.id,
            "key": p.key,
            "name": p.name,
            "role": m.role.value,
            "status": p.status.value,
        }
        for m, p in rows
    ]


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: int, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> UserPublic:
    user = await UserService(db).get_or_404(user_id)
    return UserPublic.model_validate(user)


@router.patch("/users/{user_id}/role", response_model=UserPublic)
async def update_role(
    user_id: int, payload: UserUpdateRole, request: Request,
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db),
) -> UserPublic:
    user = await UserService(db).update_role(user_id, payload.role, actor=admin, request=request)
    return UserPublic.model_validate(user)


@router.post("/users/{user_id}/deactivate", response_model=UserPublic)
async def deactivate_user(
    user_id: int, request: Request,
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db),
) -> UserPublic:
    user = await UserService(db).set_active(user_id, False, actor=admin, request=request)
    return UserPublic.model_validate(user)


@router.post("/users/{user_id}/reactivate", response_model=UserPublic)
async def reactivate_user(
    user_id: int, request: Request,
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db),
) -> UserPublic:
    user = await UserService(db).set_active(user_id, True, actor=admin, request=request)
    return UserPublic.model_validate(user)


# ── Self-service account ───────────────────────────────────────
@router.patch("/account/profile", response_model=UserPublic)
async def update_profile(
    payload: ProfileUpdate, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    updated = await UserService(db).update_profile(
        user, name=payload.name, avatar_url=payload.avatar_url
    )
    return UserPublic.model_validate(updated)


@router.post("/account/password", response_model=MessageResponse)
async def change_password(
    payload: PasswordChange, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await UserService(db).change_password(
        user, current=payload.current_password, new=payload.new_password
    )
    return MessageResponse(message="Password updated")


@router.get("/account/notification-preferences", response_model=NotificationPreferencesOut)
async def get_notification_prefs(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> NotificationPreferencesOut:
    from app.models.notification import NotificationPreference

    repo = NotificationRepository(db)
    prefs = await repo.get_preferences(user.id)
    if prefs is None:
        prefs = NotificationPreference(user_id=user.id)
        repo.add_preferences(prefs)
        await db.commit()
        await db.refresh(prefs)
    return NotificationPreferencesOut.model_validate(prefs)


@router.patch("/account/notification-preferences", response_model=NotificationPreferencesOut)
async def update_notification_prefs(
    payload: NotificationPreferencesUpdate, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferencesOut:
    from app.models.notification import NotificationPreference

    repo = NotificationRepository(db)
    prefs = await repo.get_preferences(user.id)
    if prefs is None:
        prefs = NotificationPreference(user_id=user.id)
        repo.add_preferences(prefs)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(prefs, field, value)
    await db.commit()
    await db.refresh(prefs)
    return NotificationPreferencesOut.model_validate(prefs)
