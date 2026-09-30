"""Activity feed retention: the table never grows past the configured cap."""
import pytest
from sqlalchemy import func, select

from app.models.activity import ActivityEvent
from app.services.activity_service import record_activity
from app.services.retention import prune_activity_events


async def _count(db) -> int:
    return int((await db.execute(select(func.count(ActivityEvent.id)))).scalar_one())


async def test_prune_keeps_only_the_newest(session_factory):
    async with session_factory() as db:
        for i in range(25):
            db.add(ActivityEvent(event_type="issue.created", actor_id=None, new_value=f"E-{i}"))
        await db.commit()
        assert await _count(db) == 25

        removed = await prune_activity_events(db, limit=10)
        await db.commit()

        assert removed == 15
        assert await _count(db) == 10
        # The survivors are the most recent ones.
        kept = (await db.execute(
            select(ActivityEvent.new_value)
            .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
        )).scalars().all()
        assert "E-24" in kept
        assert "E-0" not in kept


async def test_prune_is_a_noop_below_the_limit(session_factory):
    async with session_factory() as db:
        for i in range(3):
            db.add(ActivityEvent(event_type="issue.created", actor_id=None, new_value=f"E-{i}"))
        await db.commit()
        assert await prune_activity_events(db, limit=10) == 0
        assert await _count(db) == 3


async def test_recording_activity_enforces_the_cap(session_factory, monkeypatch):
    """Writing past the limit trims automatically — no scheduled job needed."""
    from app.core import config

    monkeypatch.setattr(config.settings, "activity_retention_limit", 5, raising=False)

    async with session_factory() as db:
        for i in range(12):
            await record_activity(db, event_type="issue.created", actor_id=None, new_value=f"E-{i}")
        await db.commit()
        assert await _count(db) == 5


async def test_api_respects_the_cap(client, admin, auth, session_factory):
    """Lots of real churn still leaves a bounded feed."""
    a = auth(admin)
    proj = (await client.post("/api/projects", json={"name": "Doc", "key": "DOC"}, headers=a)).json()
    meta = (await client.get("/api/meta", headers=a)).json()
    statuses = [s["id"] for s in meta["statuses"]]

    issue = (await client.post("/api/issues",
                               json={"project_id": proj["id"], "title": "churn"},
                               headers=a)).json()
    for i in range(30):
        await client.post(f"/api/issues/{issue['key']}/move", headers=a,
                          json={"status_id": statuses[i % len(statuses)]})

    async with session_factory() as db:
        from app.core.config import settings
        assert await _count(db) <= settings.activity_retention_limit

    feed = (await client.get("/api/activity?limit=100", headers=a)).json()
    assert feed["total"] <= 100
    assert feed["returned"] == feed["total"]
