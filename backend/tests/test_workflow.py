"""End-to-end style test of the V1 acceptance scenario (§111)."""
import pytest


async def _meta(client, headers):
    r = await client.get("/api/meta", headers=headers)
    assert r.status_code == 200
    m = r.json()
    return (
        {t["key"]: t["id"] for t in m["types"]},
        {s["key"]: s["id"] for s in m["statuses"]},
        {p["key"]: p["id"] for p in m["priorities"]},
    )


async def test_full_acceptance_flow(client, admin, member, member2, auth):
    a, rahul, priya = auth(admin), None, None
    rahul_user, priya_user = member, member2
    rahul, priya = auth(member), auth(member2)

    # 1. Admin creates project
    proj = (await client.post("/api/projects",
            json={"name": "Document AI", "key": "DOC"}, headers=a)).json()

    # 2. Admin adds members
    for u in (rahul_user, priya_user):
        r = await client.post(f"/api/projects/DOC/members",
                              json={"user_id": u.id, "role": "member"}, headers=a)
        assert r.status_code == 201, r.text

    types, statuses, priorities = await _meta(client, a)

    # Admin creates labels (label management is admin/PM)
    ocr = (await client.post("/api/labels", json={"name": "OCR", "color": "#8b5cf6"}, headers=a)).json()
    ml = (await client.post("/api/labels", json={"name": "ML", "color": "#3b82f6"}, headers=a)).json()

    # 3-5. Rahul creates DOC-1 assigned to Priya with all fields
    create = await client.post("/api/issues", headers=rahul, json={
        "project_id": proj["id"],
        "title": "Fix OCR extraction for cheque amount",
        "description": "Cheque amounts are misread.",
        "type_id": types["bug"], "priority_id": priorities["high"],
        "status_id": statuses["todo"], "assignee_id": priya_user.id,
        "due_date": "2026-09-12", "label_ids": [ocr["id"], ml["id"]],
    })
    assert create.status_code == 201, create.text
    issue = create.json()
    assert issue["key"] == "DOC-1"
    assert issue["assignee"]["id"] == priya_user.id
    assert {l["name"] for l in issue["labels"]} == {"OCR", "ML"}

    # 5. Priya sees it in My Issues, grouped under its workflow status
    my = (await client.get("/api/my-issues", headers=priya)).json()
    all_mine = [i["key"] for g in my["groups"] for i in g["issues"]]
    assert "DOC-1" in all_mine
    todo_group = next(g for g in my["groups"] if g["status"]["key"] == "todo")
    assert any(i["key"] == "DOC-1" for i in todo_group["issues"])

    # 6. Priya moves Todo -> In Progress
    mv = await client.post("/api/issues/DOC-1/move", headers=priya,
                           json={"status_id": statuses["in_progress"]})
    assert mv.status_code == 200, mv.text
    assert mv.json()["status"]["key"] == "in_progress"

    # 7. Activity records the status change
    acts = (await client.get("/api/issues/DOC-1/activity", headers=priya)).json()
    texts = [a["text"] for a in acts]
    assert any("changed status from Todo to In Progress" in t for t in texts)

    # 8. Priya comments
    c = await client.post("/api/issues/DOC-1/comments", headers=priya,
                          json={"body": "Looking into preprocessing."})
    assert c.status_code == 201

    # 9-10. Subtask created, marked done, parent shows 1/1
    sub = await client.post("/api/issues", headers=priya, json={
        "project_id": proj["id"], "title": "Check OCR preprocessing",
        "parent_id": issue["id"],
    })
    assert sub.status_code == 201, sub.text
    sub_key = sub.json()["key"]
    done = await client.post(f"/api/issues/{sub_key}/move", headers=priya,
                             json={"status_id": statuses["done"]})
    assert done.status_code == 200
    parent = (await client.get("/api/issues/DOC-1", headers=priya)).json()
    assert parent["subtask_total"] == 1 and parent["subtask_done"] == 1

    # 11. Relationship: DOC-1 blocks DOC-3 (create a third issue to block)
    third = await client.post("/api/issues", headers=priya, json={
        "project_id": proj["id"], "title": "API integration"})
    third_key = third.json()["key"]
    rel = await client.post("/api/issues/DOC-1/relationships", headers=priya,
                            json={"target_key": third_key, "type": "blocks"})
    assert rel.status_code == 201, rel.text
    # Visible on both sides
    src_rels = (await client.get("/api/issues/DOC-1/relationships", headers=priya)).json()
    tgt_rels = (await client.get(f"/api/issues/{third_key}/relationships", headers=priya)).json()
    assert any(r["direction"] == "outgoing" for r in src_rels)
    assert any(r["direction"] == "incoming" for r in tgt_rels)

    # Self relationship rejected
    bad = await client.post("/api/issues/DOC-1/relationships", headers=priya,
                            json={"target_key": "DOC-1", "type": "blocks"})
    assert bad.status_code == 422

    # 12. Priya changes High -> Urgent
    pr = await client.patch("/api/issues/DOC-1", headers=priya,
                            json={"priority_id": priorities["urgent"]})
    assert pr.status_code == 200
    assert pr.json()["priority"]["key"] == "urgent"

    # 13. Board shows DOC-1 under In Progress
    board = (await client.get("/api/projects/DOC/board", headers=priya)).json()
    in_prog = next(c for c in board["columns"] if c["status"]["key"] == "in_progress")
    assert any(i["key"] == "DOC-1" for i in in_prog["issues"])

    # 14. List view
    lst = (await client.get("/api/issues?project=DOC", headers=priya)).json()
    assert any(i["key"] == "DOC-1" for i in lst["items"])

    # 15. Search finds it by key, label term and description term
    for term in ("DOC-1", "OCR", "cheque"):
        res = (await client.get(f"/api/search?q={term}", headers=priya)).json()
        assert any(i["key"] == "DOC-1" for i in res["issues"]), f"search {term} failed"

    # 16. Audit log has entries for admin
    audit = (await client.get("/api/audit-logs", headers=a)).json()
    actions = {e["action"] for e in audit["items"]}
    assert "project.created" in actions
    assert "issue.created" in actions


async def test_issue_key_sequence_is_per_project(client, admin, auth):
    a = auth(admin)
    p1 = (await client.post("/api/projects", json={"name": "Alpha", "key": "ALP"}, headers=a)).json()
    p2 = (await client.post("/api/projects", json={"name": "Beta", "key": "BET"}, headers=a)).json()
    i1 = (await client.post("/api/issues", json={"project_id": p1["id"], "title": "a"}, headers=a)).json()
    i2 = (await client.post("/api/issues", json={"project_id": p1["id"], "title": "b"}, headers=a)).json()
    i3 = (await client.post("/api/issues", json={"project_id": p2["id"], "title": "c"}, headers=a)).json()
    assert i1["key"] == "ALP-1"
    assert i2["key"] == "ALP-2"
    assert i3["key"] == "BET-1"


async def test_duplicate_project_key_rejected(client, admin, auth):
    a = auth(admin)
    await client.post("/api/projects", json={"name": "One", "key": "DUP"}, headers=a)
    r = await client.post("/api/projects", json={"name": "Two", "key": "DUP"}, headers=a)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "PROJECT_KEY_TAKEN"
