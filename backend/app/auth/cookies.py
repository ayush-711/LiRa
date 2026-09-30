"""Auth cookie helpers (httpOnly session cookies + CSRF double-submit token)."""
from __future__ import annotations

from fastapi import Response

from app.auth.security import generate_secret_token
from app.core.config import settings

ACCESS_COOKIE = "lira_access"
REFRESH_COOKIE = "lira_refresh"
CSRF_COOKIE = "lira_csrf"
CSRF_HEADER = "x-csrf-token"


def _common(max_age: int, http_only: bool) -> dict:
    kwargs = dict(
        max_age=max_age,
        httponly=http_only,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    return kwargs


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> str:
    """Set session cookies and return a fresh CSRF token (also set as a cookie)."""
    response.set_cookie(
        ACCESS_COOKIE, access_token,
        **_common(settings.access_token_expire_minutes * 60, http_only=True),
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh_token,
        **_common(settings.refresh_token_expire_days * 86400, http_only=True),
    )
    csrf = generate_secret_token(24)
    # CSRF cookie is readable by JS so the SPA can echo it back in a header.
    response.set_cookie(
        CSRF_COOKIE, csrf,
        **_common(settings.refresh_token_expire_days * 86400, http_only=False),
    )
    return csrf


def clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/", domain=settings.cookie_domain or None)
