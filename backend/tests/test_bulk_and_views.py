"""Bulk issue operations, saved views, project restore and rate limiting."""


async def _project_with_issues(client, admin, auth, n=3):
    a = auth(admin)
    proj = (await client.post("/api/projects", json={"name": "Doc", "key": "DOC"}, headers=a)).json()
    keys = []
    for i in range(n):
        r = await client.post("/api/issues", headers=a,
                              json={"project_id": proj["id"], "title": f"Issue {i}"})
        keys.append(r.json()["key"])
    return proj, keys


# ── Bulk operations ────────────────────────────────────────────
async def test_bulk_change_priority(client, admin, auth):
    a = auth(admin)
    _, keys = await _project_with_issues(client, admin, auth)
    meta = (await client.get("/api/meta", headers=a)).json()
    urgent = next(p["id"] for p in meta["priorities"] if p["key"] == "urgent")

    r = await client.post("/api/issues/bulk", headers=a,
                          json={"keys": keys, "priority_id": urgent})
    assert r.status_code == 200, r.text
    assert r.json()["updated"] == len(keys)

    for k in keys:
        issue = (await client.get(f"/api/issues/{k}", headers=a)).json()
        assert issue["priority"]["key"] == "urgent"


async def test_bulk_add_label(client, admin, auth):
    a = auth(admin)
    _, keys = await _project_with_issues(client, admin, auth, n=2)
    label = (await client.post("/api/labels", json={"name": "Prod", "color": "#a15c4e"}, headers=a)).json()

    r = await client.post("/api/issues/bulk", headers=a,
                          json={"keys": keys, "add_label_ids": [label["id"]]})
    assert r.json()["updated"] == 2
    issue = (await client.get(f"/api/issues/{keys[0]}", headers=a)).json()
    assert [l["name"] for l in issue["labels"]] == ["Prod"]


async def test_bulk_reports_failures_without_aborting(client, admin, auth):
    a = auth(admin)
    _, keys = await _project_with_issues(client, admin, auth, n=2)
    r = await client.post("/api/issues/bulk", headers=a,
                          json={"keys": keys + ["DOC-999"], "archive": True})
    body = r.json()
    assert body["updated"] == 2
    assert len(body["failed"]) == 1
    assert body["failed"][0]["key"] == "DOC-999"


async def test_bulk_respects_permissions(client, admin, viewer, auth):
    _, keys = await _project_with_issues(client, admin, auth, n=2)
    r = await client.post("/api/issues/bulk", headers=auth(viewer),
                          json={"keys": keys, "archive": True})
    assert r.status_code == 200
    assert r.json()["updated"] == 0
    assert len(r.json()["failed"]) == 2


# ── Saved views ────────────────────────────────────────────────
async def test_saved_view_crud(client, member, auth):
    h = auth(member)
    created = await client.post("/api/saved-views", headers=h, json={
        "name": "My urgent work", "filters": {"mine": True, "priority": "1"},
    })
    assert created.status_code == 201, created.text
    view_id = created.json()["id"]

    listed = (await client.get("/api/saved-views", headers=h)).json()
    assert any(v["id"] == view_id for v in listed)

    renamed = await client.patch(f"/api/saved-views/{view_id}", headers=h,
                                 json={"name": "Renamed"})
    assert renamed.json()["name"] == "Renamed"

    assert (await client.delete(f"/api/saved-views/{view_id}", headers=h)).status_code == 200


async def test_cannot_modify_someone_elses_view(client, member, member2, auth):
    created = await client.post("/api/saved-views", headers=auth(member),
                                json={"name": "Private", "filters": {}})
    view_id = created.json()["id"]
    r = await client.patch(f"/api/saved-views/{view_id}", headers=auth(member2),
                           json={"name": "Hacked"})
    assert r.status_code == 403


async def test_shared_views_are_visible_to_others(client, member, member2, auth):
    await client.post("/api/saved-views", headers=auth(member),
                      json={"name": "Team view", "filters": {}, "is_shared": True})
    listed = (await client.get("/api/saved-views", headers=auth(member2))).json()
    assert any(v["name"] == "Team view" for v in listed)


# ── Project restore ────────────────────────────────────────────
async def test_archive_then_restore_project(client, admin, auth):
    a = auth(admin)
    await client.post("/api/projects", json={"name": "Doc", "key": "DOC"}, headers=a)
    assert (await client.post("/api/projects/DOC/archive", headers=a)).json()["status"] == "archived"
    restored = await client.post("/api/projects/DOC/unarchive", headers=a)
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


async def test_only_admin_can_restore(client, admin, member, auth):
    a = auth(admin)
    proj = (await client.post("/api/projects", json={"name": "Doc", "key": "DOC"}, headers=a)).json()
    await client.post("/api/projects/DOC/members",
                      json={"user_id": member.id, "role": "manager"}, headers=a)
    await client.post("/api/projects/DOC/archive", headers=a)
    r = await client.post("/api/projects/DOC/unarchive", headers=auth(member))
    assert r.status_code == 403


# ── Rate limiting ──────────────────────────────────────────────
async def test_auth_endpoint_is_ip_rate_limited(client):
    """Many login attempts from one source get throttled regardless of account."""
    codes = []
    for i in range(25):
        r = await client.post("/api/auth/login",
                              json={"email": f"nobody{i}@test.com", "password": "x"})
        codes.append(r.status_code)
    assert 429 in codes, "expected the IP rate limiter to kick in"
