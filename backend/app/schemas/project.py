from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProjectRole, ProjectStatus
from app.schemas.user import UserPublic


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    key: str = Field(min_length=2, max_length=10)
    description: str | None = None
    lead_id: int | None = None
    priority: str | None = None
    start_date: dt.date | None = None
    target_date: dt.date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=160)
    description: str | None = None
    lead_id: int | None = None
    priority: str | None = None
    status: ProjectStatus | None = None
    start_date: dt.date | None = None
    target_date: dt.date | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    name: str
    description: str | None = None
    status: ProjectStatus
    priority: str | None = None
    start_date: dt.date | None = None
    target_date: dt.date | None = None
    lead_id: int | None = None
    created_at: dt.datetime
    # current user's project role (populated by the router)
    my_role: ProjectRole | None = None


class ProjectMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: ProjectRole
    user: UserPublic


class MemberAdd(BaseModel):
    user_id: int
    role: ProjectRole = ProjectRole.member


class ProjectStats(BaseModel):
    total_issues: int
    open_issues: int
    in_progress: int
    done: int
    overdue: int
    urgent: int
    completion: int
