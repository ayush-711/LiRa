"""Cryptographic primitives: password hashing, JWTs, and random secret tokens.

We use well-established libraries only — Argon2 for passwords, PyJWT for tokens —
and never invent crypto. Long-lived secrets (invitations, resets) are random
URL-safe tokens; only their SHA-256 hash is stored server-side.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import secrets
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_ph = PasswordHasher()

ALGORITHM = "HS256"


# ── Passwords ──────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _ph.check_needs_rehash(password_hash)
    except Exception:
        return False


# ── JWT session tokens ─────────────────────────────────────────
def _create_token(subject: str, expires: dt.timedelta, token_type: str,
                  extra: dict[str, Any] | None = None) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: int, extra: dict[str, Any] | None = None) -> str:
    return _create_token(
        str(user_id),
        dt.timedelta(minutes=settings.access_token_expire_minutes),
        "access",
        extra,
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        str(user_id),
        dt.timedelta(days=settings.refresh_token_expire_days),
        "refresh",
    )


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """Decode & validate a JWT. Raises jwt exceptions on failure."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("unexpected token type")
    return payload


# ── Random secret tokens (invitations, password resets, CSRF) ──
def generate_secret_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_secret_token(token: str) -> str:
    """Deterministic hash for storage/lookup of long random tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
