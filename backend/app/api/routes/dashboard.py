from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import activity_to_out
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.misc_repos import ActivityRepository
from app.services.dashboard_service import DashboardService
from app.services.user_service import UserService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=dict)
async def get_dashboard(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> dict:
    service = DashboardService(db)
    workload = await UserService(db).workload_stats()
    # Only a short preview here — the full feed lives at /activity.
    recent = await ActivityRepository(db).recent(limit=5)
    return {
        "overview": await service.overview(),
        "personal": await service.personal(user.id),
        "issues_by_status": await service.issues_by_status(),
        "projects": await service.project_summaries(),
        "throughput": await service.throughput(),
        "workload": [
            {"user_id": uid, **counts} for uid, counts in workload.items()
        ],
        "recent_activity": [activity_to_out(e).model_dump() for e in recent],
    }
