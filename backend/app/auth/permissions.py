"""Central authorization rules.

Pure predicate functions so the same rules are reused across services and are
unit-testable in isolation. Services fetch the caller's project membership role
and pass it in. Admins bypass project membership everywhere.

See docs/architecture.md §3 for the permission matrix these encode.
"""
from __future__ import annotations

from app.models.enums import GlobalRole, ProjectRole
from app.models.project import Project
from app.models.user import User


def is_admin(user: User) -> bool:
    return user.role == GlobalRole.admin


def is_viewer(user: User) -> bool:
    return user.role == GlobalRole.viewer


# ── Global read ────────────────────────────────────────────────
def can_read_everything(user: User) -> bool:
    """V1 visibility rule: any active user may read all projects/issues."""
    return user.is_active


# ── Projects ───────────────────────────────────────────────────
def can_create_project(user: User) -> bool:
    return is_admin(user)


def can_manage_project(user: User, member_role: ProjectRole | None) -> bool:
    """Edit project, manage members, archive."""
    return is_admin(user) or member_role == ProjectRole.manager


# ── Issues ─────────────────────────────────────────────────────
def can_write_in_project(
    user: User, project: Project, member_role: ProjectRole | None
) -> bool:
    """Create/edit/move/assign issues, comment, attach within a project."""
    if is_viewer(user):
        return False
    if project.is_archived:
        # Only admins may touch issues in an archived project (e.g. to unarchive).
        return is_admin(user)
    if is_admin(user):
        return True
    # Must belong to the project (as manager or member).
    return member_role is not None


def can_create_issue(
    user: User, project: Project, member_role: ProjectRole | None
) -> bool:
    return can_write_in_project(user, project, member_role)


def can_comment(
    user: User, project: Project, member_role: ProjectRole | None
) -> bool:
    return can_write_in_project(user, project, member_role)


# ── Comments (author-level) ────────────────────────────────────
def can_edit_comment(user: User, author_id: int | None) -> bool:
    return is_admin(user) or (author_id is not None and author_id == user.id)


# ── Admin surfaces ─────────────────────────────────────────────
def can_manage_users(user: User) -> bool:
    return is_admin(user)


def can_view_audit_log(user: User) -> bool:
    return is_admin(user)


def can_manage_labels(user: User) -> bool:
    # Admins and project managers may manage the global label set in V1.
    return user.role in (GlobalRole.admin, GlobalRole.project_manager)
