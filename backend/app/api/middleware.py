"""CSRF protection and request logging middleware."""
from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.auth.cookies import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER
from app.core.errors import error_body
from app.core.logging import get_logger

logger = get_logger("request")

# Module-level so tests can reset it between cases (see tests/conftest.py).
_RATE_LIMIT_HITS: dict[str, list[float]] = defaultdict(list)


def reset_rate_limits() -> None:
    """Clear rate-limit counters. Used by tests; harmless in production."""
    _RATE_LIMIT_HITS.clear()


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# Pre-auth endpoints that run before a session/CSRF cookie exists.
CSRF_EXEMPT_EXACT = {
    "/api/auth/login",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
}


def _is_csrf_exempt(path: str) -> bool:
    if path in CSRF_EXEMPT_EXACT:
        return True
    # Invitation accept: /api/invitations/{token}/accept
    if path.startswith("/api/invitations/") and path.endswith("/accept"):
        return True
    return False


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF: for unsafe methods on a cookie-authenticated request,
    require the X-CSRF-Token header to match the CSRF cookie."""

    async def dispatch(self, request: Request, call_next):
        if (
            request.method not in SAFE_METHODS
            and request.url.path.startswith("/api")
            and ACCESS_COOKIE in request.cookies  # only browser cookie sessions
            and not _is_csrf_exempt(request.url.path)
        ):
            cookie_token = request.cookies.get(CSRF_COOKIE)
            header_token = request.headers.get(CSRF_HEADER)
            if not cookie_token or cookie_token != header_token:
                return JSONResponse(
                    status_code=403,
                    content=error_body("CSRF_FAILED", "Invalid or missing CSRF token"),
                )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window limit on unauthenticated auth endpoints.

    Complements the per-account lockout in AuthService: that stops password
    guessing against one user, this stops a single source hammering the auth
    surface across many accounts.

    In-memory and therefore per-process — appropriate for a single-node
    deployment; move to Redis if the backend is ever replicated.
    """

    LIMITED_PREFIXES = (
        "/api/auth/login",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/invitations/",
    )

    def __init__(self, app, limit: int, window_seconds: int) -> None:
        super().__init__(app)
        self.limit = limit
        self.window = window_seconds
        self._hits = _RATE_LIMIT_HITS

    def _client_ip(self, request: Request) -> str:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "POST" and path.startswith(self.LIMITED_PREFIXES):
            now = time.time()
            ip = self._client_ip(request)
            hits = self._hits[ip]
            # Drop entries outside the window, then test.
            cutoff = now - self.window
            hits[:] = [t for t in hits if t > cutoff]
            if len(hits) >= self.limit:
                logger.warning("Rate limit hit for %s on %s", ip, path)
                return JSONResponse(
                    status_code=429,
                    content=error_body(
                        "RATE_LIMITED",
                        "Too many attempts. Please wait a few minutes and try again.",
                    ),
                )
            hits.append(now)
        return await call_next(request)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        if request.url.path.startswith("/api") and request.url.path != "/api/health":
            logger.info(
                "%s %s -> %s (%.0fms)",
                request.method, request.url.path, response.status_code, elapsed,
            )
        return response
