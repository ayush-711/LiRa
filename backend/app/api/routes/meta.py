from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.reference_repo import ReferenceRepository
from app.schemas.meta import MetaOut, PriorityOut, StatusOut, TypeOut

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("", response_model=MetaOut)
async def get_meta(
    _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MetaOut:
    ref = ReferenceRepository(db)
    return MetaOut(
        statuses=[StatusOut.model_validate(s) for s in await ref.statuses()],
        types=[TypeOut.model_validate(t) for t in await ref.types()],
        priorities=[PriorityOut.model_validate(p) for p in await ref.priorities()],
    )
