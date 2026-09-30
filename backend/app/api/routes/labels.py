from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.label import LabelCreate, LabelOut, LabelUpdate
from app.services.label_service import LabelService

router = APIRouter(prefix="/labels", tags=["labels"])


@router.get("", response_model=list[LabelOut])
async def list_labels(
    include_archived: bool = False,
    _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[LabelOut]:
    rows = await LabelService(db).list(include_archived=include_archived)
    return [LabelOut.model_validate(l) for l in rows]


@router.post("", response_model=LabelOut, status_code=201)
async def create_label(
    payload: LabelCreate, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabelOut:
    label = await LabelService(db).create(
        actor=user, name=payload.name, color=payload.color, description=payload.description
    )
    return LabelOut.model_validate(label)


@router.patch("/{label_id}", response_model=LabelOut)
async def update_label(
    label_id: int, payload: LabelUpdate, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabelOut:
    label = await LabelService(db).update(
        label_id, actor=user, changes=payload.model_dump(exclude_unset=True)
    )
    return LabelOut.model_validate(label)
