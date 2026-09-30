"""Saved views, issue estimates, due-reminder tracking, full-text search index.

Adds:
  - issues.estimate              (optional effort points)
  - issues.last_due_reminder_on  (idempotency for the daily reminder job)
  - saved_views                  (named, reusable issue filters)
  - GIN full-text index on issues(title, description)  [PostgreSQL only]
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_views_estimates_fts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

FTS_INDEX = "ix_issues_fts"
FTS_EXPR = (
    "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))"
)


def upgrade() -> None:
    op.add_column("issues", sa.Column("estimate", sa.Integer(), nullable=True))
    op.add_column("issues", sa.Column("last_due_reminder_on", sa.Date(), nullable=True))

    op.create_table(
        "saved_views",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("project_id", sa.Integer(),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_saved_views_owner_id", "saved_views", ["owner_id"])
    op.create_index("ix_saved_views_project_id", "saved_views", ["project_id"])

    # Full-text search index (PostgreSQL only; SQLite falls back to ILIKE).
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"CREATE INDEX {FTS_INDEX} ON issues USING GIN ({FTS_EXPR})")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"DROP INDEX IF EXISTS {FTS_INDEX}")
    op.drop_index("ix_saved_views_project_id", table_name="saved_views")
    op.drop_index("ix_saved_views_owner_id", table_name="saved_views")
    op.drop_table("saved_views")
    op.drop_column("issues", "last_due_reminder_on")
    op.drop_column("issues", "estimate")
