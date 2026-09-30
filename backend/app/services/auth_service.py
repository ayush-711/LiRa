"""Authentication: login (with lockout), password reset, session issuance."""
from __future__ import annotations

import datetime as dt

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    generate_secret_token,
    hash_password,
    hash_secret_token,
    needs_rehash,
    verify_password,
)
from app.core.config import settings
from app.core.errors import AuthenticationError, RateLimitError, ValidationError
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.notifications import templates
from app.notifications.channels import OutboundMessage
from app.repositories.misc_repos import PasswordResetRepository
from app.repositories.user_repo import UserRepository
from app.services.audit_service import record_audit
from app.services.notification_service import NotificationService
from app.services.password_policy import validate_password


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)

    async def authenticate(self, email: str, password: str, request: Request) -> User:
        user = await self.users.get_by_email(email)

        # Uniform failure to avoid user enumeration, but still throttle per-user.
        if user is None:
            await record_audit(
                self.db, action="login_failed", entity_type="user",
                meta={"email": email, "reason": "unknown_user"}, request=request,
            )
            await self.db.commit()
            raise AuthenticationError("Invalid email or password", code="INVALID_CREDENTIALS")

        from app.core.time import as_aware

        if user.locked_until and as_aware(user.locked_until) > _now():
            raise RateLimitError(
                "Account temporarily locked due to failed login attempts. Try again later.",
                code="ACCOUNT_LOCKED",
            )

        if not user.is_active:
            raise AuthenticationError("This account is deactivated", code="ACCOUNT_INACTIVE")

        if not verify_password(password, user.password_hash):
            user.failed_login_count += 1
            if user.failed_login_count >= settings.login_max_attempts:
                user.locked_until = _now() + dt.timedelta(minutes=settings.login_lockout_minutes)
                user.failed_login_count = 0
            await record_audit(
                self.db, action="login_failed", actor_id=user.id, entity_type="user",
                entity_id=user.id, request=request,
            )
            await self.db.commit()
            raise AuthenticationError("Invalid email or password", code="INVALID_CREDENTIALS")

        # Success
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = _now()
        if needs_rehash(user.password_hash or ""):
            user.password_hash = hash_password(password)
        await record_audit(
            self.db, action="login", actor_id=user.id, entity_type="user",
            entity_id=user.id, request=request,
        )
        await self.db.commit()
        return user

    @staticmethod
    def issue_tokens(user: User) -> tuple[str, str]:
        return (
            create_access_token(user.id, extra={"role": user.role.value}),
            create_refresh_token(user.id),
        )

    async def request_password_reset(self, email: str) -> None:
        """Always succeeds silently (no user enumeration). Emails a reset link if
        the account exists."""
        user = await self.users.get_by_email(email)
        if user is None or not user.is_active:
            return
        raw = generate_secret_token(32)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_secret_token(raw),
            expires_at=_now() + dt.timedelta(hours=settings.password_reset_expire_hours),
        )
        PasswordResetRepository(self.db).add(token)

        reset_url = f"{settings.app_base_url.rstrip('/')}/reset-password/{raw}"
        subject, text, html = templates.password_reset(reset_url)
        notifier = NotificationService(self.db)
        notifier.queue_email(
            OutboundMessage(user.email, user.name, subject, text, html)
        )
        await self.db.commit()
        await notifier.flush()

    async def reset_password(self, raw_token: str, new_password: str, request: Request) -> None:
        validate_password(new_password)
        repo = PasswordResetRepository(self.db)
        token = await repo.get_by_hash(hash_secret_token(raw_token))
        from app.core.time import as_aware

        if token is None or token.used_at is not None or as_aware(token.expires_at) < _now():
            raise ValidationError("This reset link is invalid or has expired",
                                  code="RESET_TOKEN_INVALID")
        user = await self.users.get(token.user_id)
        if user is None:
            raise ValidationError("Account not found", code="USER_NOT_FOUND")
        user.password_hash = hash_password(new_password)
        user.failed_login_count = 0
        user.locked_until = None
        token.used_at = _now()
        await record_audit(
            self.db, action="password_reset", actor_id=user.id, entity_type="user",
            entity_id=user.id, request=request,
        )
        await self.db.commit()
