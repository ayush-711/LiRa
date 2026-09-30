"""Centralised notification logic.

Creates in-app notification rows (committed inside the caller's transaction) and
queues emails that are dispatched *after* commit via ``flush()`` so a rolled-back
change never emails anyone and an SMTP failure never fails the request.

Channels are pluggable (``EmailNotificationChannel`` today). Respecting user
preferences happens here so call sites stay simple.
"""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.notifications.channels import EmailNotificationChannel, OutboundMessage
from app.repositories.misc_repos import NotificationRepository

logger = get_logger("notifications")

# Registered outbound channels. Append SlackNotificationChannel() etc. later.
_CHANNELS = [EmailNotificationChannel()]


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = NotificationRepository(db)
        self._pending: list[OutboundMessage] = []
        # Recipients to ping over the websocket once the transaction commits.
        self._notified_user_ids: set[int] = set()

    async def _prefs(self, user_id: int) -> NotificationPreference:
        prefs = await self.repo.get_preferences(user_id)
        if prefs is None:
            prefs = NotificationPreference(user_id=user_id)
            self.repo.add_preferences(prefs)
        return prefs

    async def create(
        self,
        *,
        recipient: User,
        type: str,
        title: str,
        body: str | None = None,
        issue_id: int | None = None,
        actor: User | None = None,
        meta: dict | None = None,
        email: tuple[str, str, str] | None = None,
        email_pref_attr: str | None = None,
    ) -> Notification | None:
        """Create an in-app notification (and optionally queue an email).

        - ``email`` is a (subject, text, html) tuple built by a template.
        - ``email_pref_attr`` names the NotificationPreference flag gating the email.
        Don't notify a user about their own action.
        """
        if actor and actor.id == recipient.id:
            return None
        if not recipient.is_active:
            return None

        notification = Notification(
            user_id=recipient.id,
            type=type,
            title=title,
            body=body,
            issue_id=issue_id,
            actor_id=actor.id if actor else None,
            meta=meta,
        )
        self.repo.add(notification)
        self._notified_user_ids.add(recipient.id)

        if email and email_pref_attr:
            prefs = await self._prefs(recipient.id)
            if getattr(prefs, email_pref_attr, True):
                subject, text, html = email
                self._pending.append(
                    OutboundMessage(
                        to_email=recipient.email,
                        to_name=recipient.name,
                        subject=subject,
                        text_body=text,
                        html_body=html,
                    )
                )
        return notification

    def queue_email(self, message: OutboundMessage) -> None:
        """Queue a transactional email not tied to an in-app notification
        (invitations, password resets)."""
        self._pending.append(message)

    async def flush(self) -> None:
        """Dispatch queued emails and realtime pings after the transaction commits.

        Fire-and-forget: failures are logged inside each channel and never raise.
        """
        pending, self._pending = self._pending, []
        for message in pending:
            for channel in _CHANNELS:
                asyncio.create_task(channel.deliver(message))

        recipients, self._notified_user_ids = self._notified_user_ids, set()
        if recipients:
            from app.realtime.manager import manager

            for user_id in recipients:
                asyncio.create_task(
                    manager.send_to_user(user_id, {"type": "notification"})
                )
