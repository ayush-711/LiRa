from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RelationshipType
from app.schemas.label import LabelOut
from app.schemas.meta import PriorityOut, StatusOut, TypeOut
from app.schemas.user import UserPublic


class IssueSummary(BaseModel):
    """Compact issue for boards, lists, search, relationships."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    title: str
    project_id: int
    project_key: str | None = None
    type: TypeOut
    status: StatusOut
    priority: PriorityOut
    assignee: UserPublic | None = None
    reporter: UserPublic | None = None
    labels: list[LabelOut] = []
    due_date: dt.date | None = None
    estimate: int | None = None
    parent_id: int | None = None
    board_rank: float = 0.0
    is_overdue: bool = False
    updated_at: dt.datetime
    created_at: dt.datetime


class RelatedIssue(BaseModel):
    relationship_id: int
    type: RelationshipType
    direction: str  # "outgoing" | "incoming"
    issue: IssueSummary


class IssueDetail(IssueSummary):
    description: str | None = None
    resolved_at: dt.datetime | None = None
    completed_at: dt.datetime | None = None
    subtask_total: int = 0
    subtask_done: int = 0
    comment_count: int = 0
    attachment_count: int = 0


class IssueCreate(BaseModel):
    project_id: int | None = None  # optional when created under /projects/{key}/issues
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    type_id: int | None = None
    status_id: int | None = None
    priority_id: int | None = None
    assignee_id: int | None = None
    due_date: dt.date | None = None
    estimate: int | None = Field(None, ge=0, le=1000)
    parent_id: int | None = None
    label_ids: list[int] | None = None


class IssueUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    type_id: int | None = None
    status_id: int | None = None
    priority_id: int | None = None
    assignee_id: int | None = None
    due_date: dt.date | None = None
    estimate: int | None = Field(None, ge=0, le=1000)
    label_ids: list[int] | None = None

    model_config = ConfigDict(extra="forbid")


class IssueMove(BaseModel):
    status_id: int
    rank: float | None = None


class BulkUpdate(BaseModel):
    """Apply the same change to several issues.

    Each issue is authorized and audited individually — this is a convenience
    wrapper over the single-issue path, not a privileged bypass.
    """
    keys: list[str] = Field(min_length=1, max_length=100)
    status_id: int | None = None
    priority_id: int | None = None
    assignee_id: int | None = None
    add_label_ids: list[int] | None = None
    remove_label_ids: list[int] | None = None
    archive: bool | None = None


class BulkResult(BaseModel):
    updated: int
    failed: list[dict]


class RelationshipCreate(BaseModel):
    target_key: str
    type: RelationshipType


class BoardColumn(BaseModel):
    status: StatusOut
    issues: list[IssueSummary]


class BoardOut(BaseModel):
    columns: list[BoardColumn]
