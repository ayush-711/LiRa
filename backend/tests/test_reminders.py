"""Due-date reminder job: sends once per issue per day, respects state."""
import datetime as dt

from sqlalchemy import select

from app.models.issue import Issue
from app.models.notification import Notification
from app.services.reminders import run_due_reminders


async def _setup_issue(client, admin, member, auth, due: dt.date):
    a = auth(admin)
    proj = (await client.post("/api/projects", json={"name": "Doc", "key": "DOC"}, headers=a)).json()
    await client.post("/api/projects/DOC/members",
                      json={"user_id": member.id, "role": "member"}, headers=a)
    r = await client.post("/api/issues", headers=a, json={
        "project_id": proj["id"], "title": "Overdue thing",
        "assignee_id": member.id, "due_date": due.isoformat(),
    })
    assert r.status_code == 201, r.text
    return r.json()


async def test_overdue_issue_triggers_reminder(client, admin, member, auth, session_factory):
    yesterday = dt.date.today() - dt.timedelta(days=1)
    issue = await _setup_issue(client, admin, member, auth, yesterday)

    async with session_factory() as db:
        sent = await run_due_reminders(db)
    assert sent == 1

    async with session_factory() as db:
        notes = (await db.execute(
            select(Notification).where(Notification.user_id == member.id)
        )).scalars().all()
        assert any(n.type == "overdue" for n in notes)

        row = (await db.execute(
            select(Issue).where(Issue.key == issue["key"])
        )).scalar_one()
        assert row.last_due_reminder_on == dt.date.today()


async def test_reminder_is_not_sent_twice_same_day(client, admin, member, auth, session_factory):
    await _setup_issue(client, admin, member, auth, dt.date.today())

    async with session_factory() as db:
        assert await run_due_reminders(db) == 1
    async with session_factory() as db:
        assert await run_due_reminders(db) == 0  # idempotent


async def test_far_future_issue_is_not_reminded(client, admin, member, auth, session_factory):
    await _setup_issue(client, admin, member, auth, dt.date.today() + dt.timedelta(days=30))
    async with session_factory() as db:
        assert await run_due_reminders(db) == 0


async def test_done_issue_is_not_reminded(client, admin, member, auth, session_factory):
    issue = await _setup_issue(client, admin, member, auth, dt.date.today() - dt.timedelta(days=2))
    meta = (await client.get("/api/meta", headers=auth(admin))).json()
    done = next(s["id"] for s in meta["statuses"] if s["key"] == "done")
    await client.post(f"/api/issues/{issue['key']}/move", headers=auth(admin),
                      json={"status_id": done})

    async with session_factory() as db:
        assert await run_due_reminders(db) == 0
