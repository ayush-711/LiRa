from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import issue_to_summary
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.misc import SearchProjectHit
from app.schemas.user import UserPublic
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=dict)
async def global_search(
    q: str = Query(min_length=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    results = await SearchService(db).search(q)
    return {
        "issues": [issue_to_summary(i).model_dump() for i in results["issues"]],
        "projects": [SearchProjectHit.model_validate(p).model_dump() for p in results["projects"]],
        "users": [UserPublic.model_validate(u).model_dump() for u in results["users"]],
    }
