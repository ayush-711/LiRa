"""Global search across issues, projects, users and comments.

On PostgreSQL this uses full-text search (``websearch_to_tsquery`` against the
GIN index added in migration 0002), which handles stemming and multi-word
queries and stays fast as the issue count grows. Anywhere else (SQLite in tests)
it falls back to ILIKE. An exact issue-key match is always tried first so typing
"DOC-124" jumps straight to that issue.
"""
from __future__ import annotations

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.issue import Issue
from app.models.project import Project
from app.models.user import User
from app.repositories.issue_repo import display_options


class SearchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _issue_match(self, q: str, like: str):
        """Match clause for issues: key prefix always, plus FTS on Postgres or
        ILIKE elsewhere."""
        key_match = Issue.key.ilike(like)
        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            tsvector = func.to_tsvector(
                "english",
                func.coalesce(Issue.title, "") + " " + func.coalesce(Issue.description, ""),
            )
            return or_(key_match, tsvector.op("@@")(func.websearch_to_tsquery("english", q)))
        return or_(
            key_match,
            Issue.title.ilike(like),
            cast(Issue.description, String).ilike(like),
        )

    async def search(self, query: str, *, limit: int = 8) -> dict:
        q = query.strip()
        if not q:
            return {"issues": [], "projects": [], "users": []}
        like = f"%{q}%"

        issue_rows = (
            await self.db.execute(
                select(Issue)
                .where(Issue.archived_at.is_(None), self._issue_match(q, like))
                .options(*display_options())
                .order_by(Issue.updated_at.desc())
                .limit(limit)
            )
        ).scalars().unique().all()

        # Also surface issues found via matching comments (not already in results).
        if len(issue_rows) < limit:
            found_ids = {i.id for i in issue_rows}
            comment_issue_ids = (
                await self.db.execute(
                    select(Comment.issue_id)
                    .where(Comment.deleted_at.is_(None), Comment.body.ilike(like))
                    .limit(limit)
                )
            ).scalars().all()
            extra_ids = [cid for cid in comment_issue_ids if cid not in found_ids][: limit - len(issue_rows)]
            if extra_ids:
                extra = (
                    await self.db.execute(
                        select(Issue).where(Issue.id.in_(extra_ids), Issue.archived_at.is_(None))
                        .options(*display_options())
                    )
                ).scalars().unique().all()
                issue_rows = list(issue_rows) + list(extra)

        projects = (
            await self.db.execute(
                select(Project)
                .where(or_(Project.name.ilike(like), Project.key.ilike(like)))
                .order_by(Project.name).limit(limit)
            )
        ).scalars().all()

        users = (
            await self.db.execute(
                select(User)
                .where(User.is_active.is_(True),
                       or_(User.name.ilike(like), User.email.ilike(like)))
                .order_by(User.name).limit(limit)
            )
        ).scalars().all()

        return {"issues": issue_rows, "projects": projects, "users": users}
