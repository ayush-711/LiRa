"""FastAPI dependencies: DB session, current user, and role guards."""
from __future__ import annotations

import jwt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import ACCESS_COOKIE
from app.auth.security import decode_token
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.repositories.user_repo import UserRepository

# Re-export so routers can `from app.core.deps import get_db`
__all__ = ["get_db", "get_current_user", "require_roles", "require_admin", "get_current_user_optional"]


async def _load_user_from_request(request: Request, db: AsyncSession) -> User | None:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        # Allow Authorization: Bearer for API clients/tests.
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:]
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Session expired", code="SESSION_EXPIRED")
    except jwt.PyJWTError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = await UserRepository(db).get(int(user_id))
    if user is None or not user.is_active:
        return None
    return user


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    user = await _load_user_from_request(request, db)
    if user is None:
        raise AuthenticationError("Authentication required")
    return user


async def get_current_user_optional(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User | None:
    return await _load_user_from_request(request, db)


def require_roles(*roles: GlobalRole):
    """Dependency factory guarding an endpoint to the given global roles."""

    async def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise PermissionDeniedError(
                "You do not have permission to perform this action"
            )
        return user

    return _guard


require_admin = require_roles(GlobalRole.admin)
