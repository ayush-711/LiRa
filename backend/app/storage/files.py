"""Safe local file storage for attachments.

- Files are written under UPLOAD_ROOT, namespaced by project/issue.
- Stored filenames are random (uuid) so user-supplied names can never cause path
  traversal or collisions; the original name is kept only as metadata.
- Size and MIME/extension are validated before persisting.
- Raw directories are never served directly; downloads go through an
  authenticated endpoint that streams by attachment id.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.errors import ValidationError

# Conservative allowlist suitable for an internal tool.
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    ".pdf", ".txt", ".md", ".csv", ".log",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".json", ".yaml", ".yml",
}

ALLOWED_MIME_PREFIXES = ("image/", "text/", "application/")


def _safe_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File type '{ext or 'unknown'}' is not allowed",
            code="ATTACHMENT_TYPE_NOT_ALLOWED",
        )
    return ext


def validate_upload(filename: str, content_type: str, size_bytes: int) -> None:
    if size_bytes <= 0:
        raise ValidationError("Empty file", code="ATTACHMENT_EMPTY")
    if size_bytes > settings.max_upload_size_bytes:
        raise ValidationError(
            f"File exceeds the {settings.max_upload_size_mb} MB limit",
            code="ATTACHMENT_TOO_LARGE",
        )
    _safe_extension(filename)
    if content_type and not content_type.startswith(ALLOWED_MIME_PREFIXES):
        raise ValidationError(
            f"Content type '{content_type}' is not allowed",
            code="ATTACHMENT_TYPE_NOT_ALLOWED",
        )


def build_storage_path(project_id: int, issue_id: int, filename: str) -> str:
    """Return a storage path *relative* to UPLOAD_ROOT (stored in DB)."""
    ext = _safe_extension(filename)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    return os.path.join(f"project_{project_id}", f"issue_{issue_id}", stored_name)


def absolute_path(relative_path: str) -> Path:
    root = Path(settings.upload_root).resolve()
    full = (root / relative_path).resolve()
    # Defense-in-depth: ensure the resolved path stays within UPLOAD_ROOT.
    if not str(full).startswith(str(root)):
        raise ValidationError("Invalid storage path", code="ATTACHMENT_PATH_INVALID")
    return full


async def save_bytes(relative_path: str, data: bytes) -> None:
    full = absolute_path(relative_path)
    full.parent.mkdir(parents=True, exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)


def delete_file(relative_path: str) -> None:
    try:
        absolute_path(relative_path).unlink(missing_ok=True)
    except Exception:
        pass
