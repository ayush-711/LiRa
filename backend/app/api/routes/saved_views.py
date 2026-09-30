from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.saved_view import SavedView
from app.models.user import User
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/saved-views", tags=["saved-views"])


class SavedViewCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    project_id: int | None = None
    filters: dict = Field(default_factory=dict)
    is_shared: bool = False


class SavedViewUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=80)
    filters: dict | None = None
    is_shared: bool | None = None


class SavedViewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    project_id: int | None
    filters: dict
    is_shared: bool
    owner_id: int
    created_at: dt.datetime


@router.get("", response_model=list[SavedViewOut])
async def list_views(
    project_id: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SavedViewOut]:
    """Own views plus any shared by teammates."""
    stmt = select(SavedView).where(
        or_(SavedView.owner_id == user.id, SavedView.is_shared.is_(True))
    ).order_by(SavedView.name)
    if project_id is not None:
        stmt = stmt.where(
            or_(SavedView.project_id == project_id, SavedView.project_id.is_(None))
        )
    rows = (await db.execute(stmt)).scalars().all()
    return [SavedViewOut.model_validate(v) for v in rows]


@router.post("", response_model=SavedViewOut, status_code=201)
async def create_view(
    payload: SavedViewCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedViewOut:
    view = SavedView(
        owner_id=user.id, name=payload.name.strip(), project_id=payload.project_id,
        filters=payload.filters, is_shared=payload.is_shared,
    )
    db.add(view)
    await db.commit()
    await db.refresh(view)
    return SavedViewOut.model_validate(view)


async def _own_or_404(db: AsyncSession, view_id: int, user: User) -> SavedView:
    view = await db.get(SavedView, view_id)
    if view is None:
        raise NotFoundError("View not found", code="VIEW_NOT_FOUND")
    if view.owner_id != user.id:
        raise PermissionDeniedError("You can only modify your own views")
    return view


@router.patch("/{view_id}", response_model=SavedViewOut)
async def update_view(
    view_id: int, payload: SavedViewUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> SavedViewOut:
    view = await _own_or_404(db, view_id, user)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(view, field, value)
    await db.commit()
    await db.refresh(view)
    return SavedViewOut.model_validate(view)


@router.delete("/{view_id}", response_model=MessageResponse)
async def delete_view(
    view_id: int, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    view = await _own_or_404(db, view_id, user)
    await db.delete(view)
    await db.commit()
    return MessageResponse(message="View deleted")
