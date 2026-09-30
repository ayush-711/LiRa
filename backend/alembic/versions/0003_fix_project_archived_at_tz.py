"""Make projects.archived_at timezone-aware.

The column was created without an explicit type, so it landed as
TIMESTAMP WITHOUT TIME ZONE while the application writes timezone-aware
datetimes — PostgreSQL rejected every archive attempt with a DataError.
Existing values were written as UTC, so they are interpreted as UTC here.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_fix_project_archived_at_tz"
down_revision = "0002_views_estimates_fts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return  # SQLite has no distinct timestamptz type
    op.alter_column(
        "projects",
        "archived_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
        postgresql_using="archived_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.alter_column(
        "projects",
        "archived_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="archived_at AT TIME ZONE 'UTC'",
    )
