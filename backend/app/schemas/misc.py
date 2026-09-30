from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GlobalRole
from app.schemas.fields import Email
from app.schemas.user import UserPublic


# ── Invitations ────────────────────────────────────────────────
class InvitationCreate(BaseModel):
    email: Email
    role: GlobalRole = GlobalRole.member


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: GlobalRole
    created_at: dt.datetime
    expires_at: dt.datetime
    accepted_at: dt.datetime | None = None
    revoked_at: dt.datetime | None = None
    is_pending: bool


class InvitationInfo(BaseModel):
    """Public info shown on the accept page (no secrets)."""
    email: str
    role: GlobalRole


class InvitationAccept(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=200)


# ── Comments ───────────────────────────────────────────────────
class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    body: str
    author: UserPublic | None = None
    created_at: dt.datetime
    edited_at: dt.datetime | None = None


# ── Attachments ────────────────────────────────────────────────
class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_by: UserPublic | None = None
    created_at: dt.datetime


# ── Notifications ──────────────────────────────────────────────
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    title: str
    body: str | None = None
    issue_id: int | None = None
    actor: UserPublic | None = None
    is_read: bool
    created_at: dt.datetime
    meta: dict | None = None


class NotificationPreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email_on_assignment: bool
    email_on_mention: bool
    email_on_comment: bool
    email_on_due_reminder: bool
    email_on_status_change: bool


class NotificationPreferencesUpdate(BaseModel):
    email_on_assignment: bool | None = None
    email_on_mention: bool | None = None
    email_on_comment: bool | None = None
    email_on_due_reminder: bool | None = None
    email_on_status_change: bool | None = None


# ── Activity ───────────────────────────────────────────────────
class ActivityOut(BaseModel):
    id: int
    event_type: str
    actor: UserPublic | None = None
    field: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    created_at: dt.datetime
    text: str  # rendered human-readable sentence


# ── Audit ──────────────────────────────────────────────────────
class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    action: str
    actor: UserPublic | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    meta: dict | None = None
    ip_address: str | None = None
    created_at: dt.datetime


# ── Search ─────────────────────────────────────────────────────
class SearchProjectHit(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    name: str
