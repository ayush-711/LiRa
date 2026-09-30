from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import NotFoundError
from app.models.user import User
from app.schemas.common import MessageResponse
from app.services.attachment_service import AttachmentService
from app.storage import files

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: int, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Authenticated download. Files are streamed from private storage — the
    upload directory is never served directly."""
    att = await AttachmentService(db).get_or_404(attachment_id)
    path = files.absolute_path(att.storage_path)
    if not path.exists():
        raise NotFoundError("File is missing from storage", code="ATTACHMENT_FILE_MISSING")
    return FileResponse(
        path, media_type=att.content_type, filename=att.original_filename
    )


@router.delete("/{attachment_id}", response_model=MessageResponse)
async def delete_attachment(
    attachment_id: int, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await AttachmentService(db).delete(attachment_id, actor=user)
    return MessageResponse(message="Attachment deleted")
