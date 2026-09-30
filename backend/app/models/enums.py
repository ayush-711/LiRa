"""Enumerations used across the domain.

Reference *data* (issue statuses, types, priorities) lives in DB tables so it can
be extended without code changes. These enums are for values that are structural
to the application's logic (roles, categories, relationship kinds).
"""
from __future__ import annotations

import enum


class GlobalRole(str, enum.Enum):
    admin = "admin"
    project_manager = "project_manager"
    member = "member"
    viewer = "viewer"


class ProjectRole(str, enum.Enum):
    manager = "manager"
    member = "member"


class ProjectStatus(str, enum.Enum):
    planning = "planning"
    active = "active"
    completed = "completed"
    archived = "archived"


class StatusCategory(str, enum.Enum):
    """High-level bucket a workflow status belongs to.

    Used for consistent counting (open vs done) regardless of custom names.
    """
    backlog = "backlog"
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class RelationshipType(str, enum.Enum):
    blocks = "blocks"        # source blocks target
    relates_to = "relates_to"  # symmetric relation
