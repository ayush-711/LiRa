"""Shared custom field types.

`Email` validates basic email format but — unlike pydantic's EmailStr — permits
internal/special-use domains such as ``.local``, which are common in self-hosted
internal deployments. Output schemas use plain ``str`` for emails (stored values
are already trusted and need no revalidation on the way out).
"""
from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    value = value.strip().lower()
    if not _EMAIL_RE.match(value) or len(value) > 254:
        raise ValueError("value is not a valid email address")
    return value


Email = Annotated[str, AfterValidator(_validate_email)]
