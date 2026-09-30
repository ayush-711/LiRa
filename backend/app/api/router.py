"""Aggregate all route modules under a single /api router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    activity,
    attachments,
    audit,
    auth,
    dashboard,
    health,
    invitations,
    issues,
    labels,
    meta,
    notifications,
    projects,
    search,
    saved_views,
    users,
    views,
    ws,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(activity.router)
api_router.include_router(auth.router)
api_router.include_router(invitations.router)
api_router.include_router(users.router)
api_router.include_router(meta.router)
api_router.include_router(labels.router)
api_router.include_router(projects.router)
api_router.include_router(issues.router)
api_router.include_router(views.router)
api_router.include_router(attachments.router)
api_router.include_router(notifications.router)
api_router.include_router(audit.router)
api_router.include_router(dashboard.router)
api_router.include_router(search.router)
api_router.include_router(saved_views.router)
api_router.include_router(ws.router)
