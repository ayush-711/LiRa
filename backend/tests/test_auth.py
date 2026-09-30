import pytest


async def test_login_success(client, member):
    r = await client.post("/api/auth/login",
                          json={"email": "member@test.local", "password": "Password123!"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "member@test.local"
    assert "csrf_token" in body


async def test_login_wrong_password(client, member):
    r = await client.post("/api/auth/login",
                          json={"email": "member@test.local", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_unknown_user(client):
    r = await client.post("/api/auth/login",
                          json={"email": "nobody@test.local", "password": "whatever"})
    assert r.status_code == 401


async def test_me_requires_auth(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


async def test_me_with_bearer(client, member, auth):
    r = await client.get("/api/auth/me", headers=auth(member))
    assert r.status_code == 200
    assert r.json()["email"] == "member@test.local"


async def test_lockout_after_failures(client, member):
    for _ in range(5):
        await client.post("/api/auth/login",
                          json={"email": "member@test.local", "password": "bad"})
    r = await client.post("/api/auth/login",
                          json={"email": "member@test.local", "password": "Password123!"})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "ACCOUNT_LOCKED"
