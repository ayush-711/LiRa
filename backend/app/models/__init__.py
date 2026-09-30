"""ORM models.

Importing this package registers every model on the shared ``Base.metadata`` so
that Alembic autogeneration and ``create_all`` (tests) see the full schema.
"""
from app.db.base import Base  # noqa: F401
from app.models.enums import (  # noqa: F401
    GlobalRole,
    ProjectRole,
    ProjectStatus,
    RelationshipType,
    StatusCategory,
)
from app.models.user import User  # noqa: F401
from app.models.invitation import Invitation  # noqa: F401
from app.models.password_reset import PasswordResetToken  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.project_member import ProjectMember  # noqa: F401
from app.models.reference import IssuePriority, IssueStatus, IssueType  # noqa: F401
from app.models.label import IssueLabel, Label  # noqa: F401
from app.models.issue import Issue  # noqa: F401
from app.models.issue_relationship import IssueRelationship  # noqa: F401
from app.models.comment import Comment  # noqa: F401
from app.models.attachment import Attachment  # noqa: F401
from app.models.activity import ActivityEvent  # noqa: F401
from app.models.notification import Notification, NotificationPreference  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.saved_view import SavedView  # noqa: F401

__all__ = ["Base"]
