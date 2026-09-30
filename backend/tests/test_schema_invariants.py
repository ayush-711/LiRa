"""Schema invariants that SQLite is too permissive to catch.

The test suite runs on SQLite, which happily stores timezone-aware datetimes in
a naive column. PostgreSQL does not — it raises a DataError. A single column
(projects.archived_at) shipped without an explicit type and broke archiving in
production while every test stayed green. These assertions close that gap.
"""
from sqlalchemy import DateTime

from app.models import Base


def test_all_datetime_columns_are_timezone_aware():
    """Every timestamp is stored as TIMESTAMPTZ so UTC round-trips correctly."""
    naive = [
        f"{table.name}.{col.name}"
        for table in Base.metadata.tables.values()
        for col in table.columns
        if isinstance(col.type, DateTime) and not col.type.timezone
    ]
    assert naive == [], (
        "These datetime columns are timezone-naive; PostgreSQL will reject "
        f"aware datetimes written to them: {naive}"
    )
