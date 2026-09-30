from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.fields import Email
from app.schemas.user import UserPublic


class LoginRequest(BaseModel):
    email: Email
    password: str


class LoginResponse(BaseModel):
    user: UserPublic
    csrf_token: str


class ForgotPasswordRequest(BaseModel):
    email: Email


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=200)
