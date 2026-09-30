from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserPublic
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest, request: Request, response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    service = AuthService(db)
    user = await service.authenticate(payload.email, payload.password, request)
    access, refresh = service.issue_tokens(user)
    csrf = set_auth_cookies(response, access, refresh)
    return LoginResponse(user=UserPublic.model_validate(user), csrf_token=csrf)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response, _: User = Depends(get_current_user)) -> MessageResponse:
    clear_auth_cookies(response)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    await AuthService(db).request_password_reset(payload.email)
    # Always the same response to avoid revealing which emails exist.
    return MessageResponse(message="If that email exists, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    await AuthService(db).reset_password(payload.token, payload.new_password, request)
    return MessageResponse(message="Password updated. You can now sign in.")
