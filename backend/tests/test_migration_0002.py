from __future__ import annotations

import importlib.util
from pathlib import Path


_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0002_views_estimates_fts.py"
)
_SPEC = importlib.util.spec_from_file_location("migration_0002_views_estimates_fts", _MIGRATION_PATH)
assert _SPEC is not None and _SPEC.loader is not None
migration = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(migration)


class _FakeInspector:
    def __init__(self, issue_columns: set[str], has_saved_views: bool):
        self._issue_columns = issue_columns
        self._has_saved_views = has_saved_views

    def get_columns(self, table_name: str):
        assert table_name == "issues"
        return [{"name": name} for name in sorted(self._issue_columns)]

    def has_table(self, table_name: str):
        assert table_name == "saved_views"
        return self._has_saved_views


class _FakeBind:
    def __init__(self, dialect_name: str):
        self.dialect = type("Dialect", (), {"name": dialect_name})()


def _run_upgrade(monkeypatch, *, issue_columns: set[str], has_saved_views: bool):
    bind = _FakeBind("postgresql")
    inspector = _FakeInspector(issue_columns, has_saved_views)
    added_columns: list[str] = []
    created_tables: list[str] = []
    executed_sql: list[str] = []

    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(migration.sa, "inspect", lambda _: inspector)
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table_name, column: added_columns.append(f"{table_name}.{column.name}"),
    )
    monkeypatch.setattr(
        migration.op,
        "create_table",
        lambda table_name, *args, **kwargs: created_tables.append(table_name),
    )
    monkeypatch.setattr(migration.op, "execute", lambda sql: executed_sql.append(str(sql)))

    migration.upgrade()
    return added_columns, created_tables, executed_sql


def test_upgrade_is_idempotent_when_objects_already_exist(monkeypatch):
    added_columns, created_tables, executed_sql = _run_upgrade(
        monkeypatch,
        issue_columns={"estimate", "last_due_reminder_on"},
        has_saved_views=True,
    )

    assert added_columns == []
    assert created_tables == []
    assert "CREATE INDEX IF NOT EXISTS ix_saved_views_owner_id ON saved_views (owner_id)" in executed_sql
    assert "CREATE INDEX IF NOT EXISTS ix_saved_views_project_id ON saved_views (project_id)" in executed_sql
    assert any("CREATE INDEX IF NOT EXISTS ix_issues_fts" in sql for sql in executed_sql)


def test_upgrade_creates_missing_columns_and_table(monkeypatch):
    added_columns, created_tables, executed_sql = _run_upgrade(
        monkeypatch,
        issue_columns=set(),
        has_saved_views=False,
    )

    assert sorted(added_columns) == ["issues.estimate", "issues.last_due_reminder_on"]
    assert created_tables == ["saved_views"]
    assert any("CREATE INDEX IF NOT EXISTS ix_issues_fts" in sql for sql in executed_sql)
