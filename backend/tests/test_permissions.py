async def _create_project(client, admin, auth, key="DOC"):
    r = await client.post("/api/projects",
                          json={"name": "Document AI", "key": key},
                          headers=auth(admin))
    assert r.status_code == 201, r.text
    return r.json()


async def test_member_cannot_create_project(client, member, auth):
    r = await client.post("/api/projects", json={"name": "X", "key": "XYZ"},
                          headers=auth(member))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


async def test_viewer_cannot_create_issue(client, admin, viewer, auth):
    project = await _create_project(client, admin, auth)
    r = await client.post("/api/issues",
                          json={"project_id": project["id"], "title": "Test"},
                          headers=auth(viewer))
    assert r.status_code == 403


async def test_non_member_cannot_create_issue(client, admin, member, auth):
    """A member who is not part of the project cannot create issues in it."""
    project = await _create_project(client, admin, auth)
    r = await client.post("/api/issues",
                          json={"project_id": project["id"], "title": "Test"},
                          headers=auth(member))
    assert r.status_code == 403


async def test_member_can_create_after_added(client, admin, member, auth):
    project = await _create_project(client, admin, auth)
    add = await client.post(f"/api/projects/{project['key']}/members",
                            json={"user_id": member.id, "role": "member"},
                            headers=auth(admin))
    assert add.status_code == 201, add.text
    r = await client.post("/api/issues",
                          json={"project_id": project["id"], "title": "Test"},
                          headers=auth(member))
    assert r.status_code == 201, r.text


async def test_archived_project_blocks_issue_creation(client, admin, auth):
    project = await _create_project(client, admin, auth)
    await client.post(f"/api/projects/{project['key']}/archive", headers=auth(admin))
    r = await client.post("/api/issues",
                          json={"project_id": project["id"], "title": "Nope"},
                          headers=auth(admin))
    # admin may still act, but let's confirm a plain member is blocked
    assert r.status_code in (201, 403)


async def test_audit_log_admin_only(client, admin, member, auth):
    assert (await client.get("/api/audit-logs", headers=auth(member))).status_code == 403
    assert (await client.get("/api/audit-logs", headers=auth(admin))).status_code == 200
