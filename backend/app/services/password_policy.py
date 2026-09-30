"""Minimum password policy, enforced server-side."""
from __future__ import annotations

import re

from app.core.errors import ValidationError

MIN_LENGTH = 8


def validate_password(password: str) -> None:
    if len(password) < MIN_LENGTH:
        raise ValidationError(
            f"Password must be at least {MIN_LENGTH} characters", code="PASSWORD_TOO_SHORT"
        )
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValidationError(
            "Password must contain both letters and numbers", code="PASSWORD_TOO_WEAK"
        )
