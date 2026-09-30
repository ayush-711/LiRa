"""Consistent application errors and the structured error response format.

Every error the API returns has the shape:

    {"error": {"code": "ISSUE_NOT_FOUND", "message": "Issue DOC-124 was not found"}}

Handlers raise `AppError` subclasses; a single exception handler renders them.
"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all business/HTTP errors surfaced to clients."""

    status_code: int = 400
    code: str = "BAD_REQUEST"

    def __init__(self, message: str, *, code: str | None = None,
                 status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class AuthenticationError(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class RateLimitError(AppError):
    status_code = 429
    code = "RATE_LIMITED"


def error_body(code: str, message: str, details: Any = None) -> dict:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body
