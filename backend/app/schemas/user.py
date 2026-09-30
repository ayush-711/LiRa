from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GlobalRole


class UserPublic(BaseModel):
    """Minimal user info safe to embed anywhere (assignees, authors, etc.)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    avatar_url: str | None = None
    role: GlobalRole
    is_active: bool


class UserWithStats(UserPublic):
    assigned: int = 0
    in_progress: int = 0
    overdue: int = 0
    last_login_at: dt.datetime | None = None


class UserUpdateRole(BaseModel):
    role: GlobalRole


class ProfileUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    avatar_url: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)
