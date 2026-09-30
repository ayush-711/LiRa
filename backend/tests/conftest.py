"""Test harness: in-memory async SQLite, seeded reference data, HTTP client.

Tests authenticate with a Bearer token (the API accepts Authorization: Bearer in
addition to cookies), which bypasses the browser-only CSRF check.
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.auth.security import create_access_token, hash_password
from app.core.deps import get_db
from app.main import app
from app.models import Base
from app.models.enums import GlobalRole
from app.models.notification import NotificationPreference
from app.models.user import User
from app.scripts.seed_reference import _seed_reference


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        await _seed_reference(db)
        await db.commit()
    return factory


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Rate-limit counters are process-global; clear them so tests don't leak
    into each other."""
    from app.api.middleware import reset_rate_limits

    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest_asyncio.fixture
async def client(session_factory):
    async def _get_db():
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = _get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _make_user(session_factory, email: str, role: GlobalRole, name: str) -> User:
    async with session_factory() as db:
        user = User(email=email, name=name, password_hash=hash_password("Password123!"),
                    role=role, is_active=True)
        db.add(user)
        await db.flush()
        db.add(NotificationPreference(user_id=user.id))
        await db.commit()
        await db.refresh(user)
        return user


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest_asyncio.fixture
async def admin(session_factory):
    return await _make_user(session_factory, "admin@test.local", GlobalRole.admin, "Admin")


@pytest_asyncio.fixture
async def member(session_factory):
    return await _make_user(session_factory, "member@test.local", GlobalRole.member, "Rahul")


@pytest_asyncio.fixture
async def member2(session_factory):
    return await _make_user(session_factory, "member2@test.local", GlobalRole.member, "Priya")


@pytest_asyncio.fixture
async def viewer(session_factory):
    return await _make_user(session_factory, "viewer@test.local", GlobalRole.viewer, "Val")


@pytest.fixture
def auth():
    return _auth
