"""Invitation-only registration."""
from __future__ import annotations

import datetime as dt

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import (
    generate_secret_token,
    hash_password,
    hash_secret_token,
)
from app.core.config import settings
from app.core.errors import ConflictError, ValidationError
from app.models.enums import GlobalRole
from app.models.invitation import Invitation
from app.models.notification import NotificationPreference
from app.models.user import User
from app.notifications import templates
from app.notifications.channels import OutboundMessage
from app.repositories.invitation_repo import InvitationRepository
from app.repositories.user_repo import UserRepository
from app.services.audit_service import record_audit
from app.services.notification_service import NotificationService
from app.services.password_policy import validate_password


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class InvitationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InvitationRepository(db)
        self.users = UserRepository(db)

    async def create(
        self, *, email: str, role: GlobalRole, inviter: User, request: Request
    ) -> tuple[Invitation, str]:
        email = email.strip().lower()
        if await self.users.get_by_email(email):
            raise ConflictError("A user with that email already exists",
                                code="USER_ALREADY_EXISTS")
        existing = await self.repo.get_pending_by_email(email)
        if existing and existing.is_pending:
            # Revoke the old one and issue a fresh token.
            existing.revoked_at = _now()

        raw = generate_secret_token(32)
        invitation = Invitation(
            email=email,
            role=role,
            token_hash=hash_secret_token(raw),
            created_by_id=inviter.id,
            expires_at=_now() + dt.timedelta(hours=settings.invitation_expire_hours),
        )
        self.repo.add(invitation)
        await record_audit(
            self.db, action="invitation.created", actor_id=inviter.id,
            entity_type="invitation", meta={"email": email, "role": role.value},
            request=request,
        )

        accept_url = f"{settings.app_base_url.rstrip('/')}/invite/{raw}"
        subject, text, html = templates.invitation(inviter.name, accept_url, role.value)
        notifier = NotificationService(self.db)
        notifier.queue_email(OutboundMessage(email, email, subject, text, html))

        await self.db.commit()
        await self.db.refresh(invitation)
        await notifier.flush()
        return invitation, raw

    async def get_pending_by_raw_token(self, raw_token: str) -> Invitation:
        invitation = await self.repo.get_by_token_hash(hash_secret_token(raw_token))
        if invitation is None or not invitation.is_pending:
            raise ValidationError("This invitation is invalid or has expired",
                                  code="INVITATION_INVALID")
        return invitation

    async def accept(
        self, *, raw_token: str, name: str, password: str, request: Request
    ) -> User:
        validate_password(password)
        invitation = await self.get_pending_by_raw_token(raw_token)

        if await self.users.get_by_email(invitation.email):
            raise ConflictError("This account already exists", code="USER_ALREADY_EXISTS")

        user = User(
            email=invitation.email,
            name=name.strip(),
            password_hash=hash_password(password),
            role=invitation.role,
            is_active=True,
        )
        self.users.add(user)
        await self.db.flush()  # assign user.id
        self.db.add(NotificationPreference(user_id=user.id))

        invitation.accepted_at = _now()
        await record_audit(
            self.db, action="invitation.accepted", actor_id=user.id,
            entity_type="user", entity_id=user.id,
            meta={"email": user.email}, request=request,
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def revoke(self, invitation_id: int, *, actor: User, request: Request) -> Invitation:
        invitation = await self.repo.get(invitation_id)
        if invitation is None:
            raise ValidationError("Invitation not found", code="INVITATION_NOT_FOUND")
        if invitation.is_pending:
            invitation.revoked_at = _now()
            await record_audit(
                self.db, action="invitation.revoked", actor_id=actor.id,
                entity_type="invitation", entity_id=invitation.id, request=request,
            )
            await self.db.commit()
        return invitation
