"""ORM → Pydantic serialization helpers and human-readable activity rendering."""
from __future__ import annotations

from app.models.activity import ActivityEvent
from app.models.issue import Issue
from app.schemas.issue import IssueDetail, IssueSummary
from app.schemas.label import LabelOut
from app.schemas.meta import PriorityOut, StatusOut, TypeOut
from app.schemas.misc import ActivityOut
from app.schemas.user import UserPublic
from app.services.issue_rules import is_overdue


def _labels(issue: Issue) -> list[LabelOut]:
    return [LabelOut.model_validate(il.label) for il in issue.issue_labels if il.label]


def issue_to_summary(issue: Issue) -> IssueSummary:
    return IssueSummary(
        id=issue.id,
        key=issue.key,
        title=issue.title,
        project_id=issue.project_id,
        project_key=issue.project.key if issue.project else None,
        type=TypeOut.model_validate(issue.type),
        status=StatusOut.model_validate(issue.status),
        priority=PriorityOut.model_validate(issue.priority),
        assignee=UserPublic.model_validate(issue.assignee) if issue.assignee else None,
        reporter=UserPublic.model_validate(issue.reporter) if issue.reporter else None,
        labels=_labels(issue),
        due_date=issue.due_date,
        estimate=issue.estimate,
        parent_id=issue.parent_id,
        board_rank=issue.board_rank,
        is_overdue=is_overdue(issue),
        updated_at=issue.updated_at,
        created_at=issue.created_at,
    )


def issue_to_detail(
    issue: Issue, *, subtask_total: int = 0, subtask_done: int = 0,
    comment_count: int = 0, attachment_count: int = 0,
) -> IssueDetail:
    base = issue_to_summary(issue).model_dump()
    return IssueDetail(
        **base,
        description=issue.description,
        resolved_at=issue.resolved_at,
        completed_at=issue.completed_at,
        subtask_total=subtask_total,
        subtask_done=subtask_done,
        comment_count=comment_count,
        attachment_count=attachment_count,
    )


# ── Activity rendering ─────────────────────────────────────────
def render_activity_text(ev: ActivityEvent) -> str:
    actor = ev.actor.name if ev.actor else "Someone"
    t = ev.event_type
    if t == "issue.created":
        return f"{actor} created this issue"
    if t == "issue.status_changed":
        return f"{actor} changed status from {ev.old_value} to {ev.new_value}"
    if t == "issue.priority_changed":
        return f"{actor} changed priority from {ev.old_value or 'None'} to {ev.new_value}"
    if t == "issue.assigned":
        if ev.new_value:
            return f"{actor} assigned this to {ev.new_value}"
        return f"{actor} unassigned this issue"
    if t == "comment.added":
        return f"{actor} added a comment"
    if t == "attachment.added":
        return f"{actor} attached {ev.new_value}"
    if t == "issue.archived":
        return f"{actor} archived this issue"
    if t == "project.created":
        return f"{actor} created the project"
    if t == "project.archived":
        return f"{actor} archived the project"
    if t == "project.member_added":
        return f"{actor} added {ev.new_value} to the project"
    if t == "project.member_removed":
        return f"{actor} removed a member from the project"
    return f"{actor} performed {t}"


def activity_to_out(ev: ActivityEvent) -> ActivityOut:
    return ActivityOut(
        id=ev.id,
        event_type=ev.event_type,
        actor=UserPublic.model_validate(ev.actor) if ev.actor else None,
        field=ev.field,
        old_value=ev.old_value,
        new_value=ev.new_value,
        created_at=ev.created_at,
        text=render_activity_text(ev),
    )
