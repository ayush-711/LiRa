"""Concise, mobile-friendly email templates.

Kept small and readable per the spec — a short text body plus a minimal HTML
version. `APP_BASE_URL` is used to build absolute links.
"""
from __future__ import annotations

from app.core.config import settings


def _issue_url(issue_key: str) -> str:
    return f"{settings.app_base_url.rstrip('/')}/issues/{issue_key}"


def _wrap_html(title: str, lines: list[str], button_label: str, button_url: str) -> str:
    body_lines = "".join(f"<p style='margin:4px 0;color:#334155'>{ln}</p>" for ln in lines)
    return f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:480px;margin:0 auto">
  <h2 style="color:#0f172a;font-size:18px;margin:0 0 12px">{title}</h2>
  {body_lines}
  <p style="margin:20px 0">
    <a href="{button_url}" style="background:#4f46e5;color:#fff;text-decoration:none;
       padding:9px 16px;border-radius:6px;font-size:14px;display:inline-block">{button_label}</a>
  </p>
  <p style="color:#94a3b8;font-size:12px">{settings.app_name} · internal work management</p>
</div>"""


def issue_assigned(issue_key, title, project_name, priority, due, assigned_by):
    subject = f"[{issue_key}] You were assigned an issue"
    lines = [
        f"<strong>{issue_key}</strong> — {title}",
        f"Project: {project_name}",
        f"Priority: {priority}",
        f"Due: {due or '—'}",
        f"Assigned by: {assigned_by}",
    ]
    text = (
        f"{issue_key} — {title}\nProject: {project_name}\nPriority: {priority}\n"
        f"Due: {due or '—'}\nAssigned by: {assigned_by}\n\nOpen: {_issue_url(issue_key)}"
    )
    return subject, text, _wrap_html("You were assigned an issue", lines, "Open issue", _issue_url(issue_key))


def issue_mention(issue_key, title, actor, snippet):
    subject = f"[{issue_key}] {actor} mentioned you"
    lines = [f"<strong>{issue_key}</strong> — {title}", f"{actor} mentioned you:", f"“{snippet}”"]
    text = f"{actor} mentioned you on {issue_key} — {title}\n\n{snippet}\n\nOpen: {_issue_url(issue_key)}"
    return subject, text, _wrap_html(f"{actor} mentioned you", lines, "Open issue", _issue_url(issue_key))


def issue_comment(issue_key, title, actor, snippet):
    subject = f"[{issue_key}] New comment from {actor}"
    lines = [f"<strong>{issue_key}</strong> — {title}", f"{actor} commented:", f"“{snippet}”"]
    text = f"{actor} commented on {issue_key} — {title}\n\n{snippet}\n\nOpen: {_issue_url(issue_key)}"
    return subject, text, _wrap_html("New comment", lines, "Open issue", _issue_url(issue_key))


def issue_status_changed(issue_key, title, actor, old, new):
    subject = f"[{issue_key}] Status changed to {new}"
    lines = [f"<strong>{issue_key}</strong> — {title}", f"{actor} changed status from {old} to {new}."]
    text = f"{actor} changed status of {issue_key} from {old} to {new}.\n\nOpen: {_issue_url(issue_key)}"
    return subject, text, _wrap_html("Status changed", lines, "Open issue", _issue_url(issue_key))


def issue_due_reminder(issue_key, title, project_name, due, overdue: bool):
    when = "is overdue" if overdue else "is due soon"
    subject = f"[{issue_key}] {'Overdue' if overdue else 'Due soon'}: {title}"
    lines = [
        f"<strong>{issue_key}</strong> — {title}",
        f"Project: {project_name}",
        f"Due: {due}",
        f"This issue {when} and is still open.",
    ]
    text = (
        f"{issue_key} — {title}\nProject: {project_name}\nDue: {due}\n"
        f"This issue {when} and is still open.\n\nOpen: {_issue_url(issue_key)}"
    )
    return subject, text, _wrap_html(
        "Overdue issue" if overdue else "Issue due soon", lines, "Open issue",
        _issue_url(issue_key),
    )


def invitation(inviter, accept_url, role):
    subject = f"You've been invited to {settings.app_name}"
    lines = [
        f"{inviter} invited you to join {settings.app_name} as a {role}.",
        "Click below to set your name and password.",
    ]
    text = f"{inviter} invited you to {settings.app_name} ({role}).\n\nAccept: {accept_url}"
    return subject, text, _wrap_html(f"Join {settings.app_name}", lines, "Accept invitation", accept_url)


def password_reset(reset_url):
    subject = f"Reset your {settings.app_name} password"
    lines = ["We received a request to reset your password.",
             "If this wasn't you, you can ignore this email."]
    text = f"Reset your password:\n{reset_url}"
    return subject, text, _wrap_html("Reset your password", lines, "Reset password", reset_url)
