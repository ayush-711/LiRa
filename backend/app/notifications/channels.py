"""Notification channel abstraction.

A ``NotificationChannel`` delivers an outbound message to some medium. V1 ships
``EmailNotificationChannel``; Slack/Teams/Webhook channels can be registered
later without changing any call site (they just implement ``deliver``).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass

import aiosmtplib

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("notifications")


@dataclass
class OutboundMessage:
    to_email: str
    to_name: str
    subject: str
    text_body: str
    html_body: str | None = None


class NotificationChannel(abc.ABC):
    name: str

    @abc.abstractmethod
    async def deliver(self, message: OutboundMessage) -> None:  # pragma: no cover
        ...


class EmailNotificationChannel(NotificationChannel):
    name = "email"

    async def deliver(self, message: OutboundMessage) -> None:
        if not settings.emails_enabled:
            # Dev fallback: log the email instead of sending it.
            logger.info(
                "[email:dev] To=%s <%s> | %s\n%s",
                message.to_name, message.to_email, message.subject, message.text_body,
            )
            return

        from email.message import EmailMessage

        email = EmailMessage()
        email["From"] = settings.email_from
        email["To"] = f"{message.to_name} <{message.to_email}>"
        email["Subject"] = message.subject
        email.set_content(message.text_body)
        if message.html_body:
            email.add_alternative(message.html_body, subtype="html")

        try:
            await aiosmtplib.send(
                email,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username or None,
                password=settings.smtp_password or None,
                start_tls=settings.smtp_use_tls,
                timeout=15,
            )
            logger.info("Sent email to %s: %s", message.to_email, message.subject)
        except Exception as exc:  # never let email failure break a request
            logger.error("Failed to send email to %s: %s", message.to_email, exc)


class SlackNotificationChannel(NotificationChannel):
    """Placeholder illustrating the extension point (disabled unless configured)."""

    name = "slack"

    async def deliver(self, message: OutboundMessage) -> None:  # pragma: no cover
        if not settings.slack_webhook_url:
            return
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    settings.slack_webhook_url,
                    json={"text": f"*{message.subject}*\n{message.text_body}"},
                )
        except Exception as exc:
            logger.error("Slack delivery failed: %s", exc)
