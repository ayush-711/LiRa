from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import set_auth_cookies
from app.core.deps import get_db, require_admin
from app.models.user import User
from app.schemas.auth import LoginResponse
from app.schemas.common import MessageResponse
from app.schemas.misc import (
    InvitationAccept,
    InvitationCreate,
    InvitationInfo,
    InvitationOut,
)
from app.schemas.user import UserPublic
from app.services.auth_service import AuthService
from app.services.invitation_service import InvitationService

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post("", response_model=InvitationOut, status_code=201)
async def create_invitation(
    payload: InvitationCreate, request: Request,
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db),
) -> InvitationOut:
    invitation, _raw = await InvitationService(db).create(
        email=payload.email, role=payload.role, inviter=admin, request=request
    )
    return InvitationOut.model_validate(invitation)


@router.get("", response_model=list[InvitationOut])
async def list_invitations(
    _: User = Depends(require_admin), db: AsyncSession = Depends(get_db),
    limit: int = 100, offset: int = 0,
) -> list[InvitationOut]:
    rows = await InvitationService(db).repo.list(limit=limit, offset=offset)
    return [InvitationOut.model_validate(r) for r in rows]


@router.get("/{token}", response_model=InvitationInfo)
async def get_invitation(token: str, db: AsyncSession = Depends(get_db)) -> InvitationInfo:
    """Public: show which email/role an invite is for, so the accept page can
    display it. No secrets returned."""
    invitation = await InvitationService(db).get_pending_by_raw_token(token)
    return InvitationInfo(email=invitation.email, role=invitation.role)


@router.post("/{token}/accept", response_model=LoginResponse)
async def accept_invitation(
    token: str, payload: InvitationAccept, request: Request, response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    service = InvitationService(db)
    user = await service.accept(
        raw_token=token, name=payload.name, password=payload.password, request=request
    )
    access, refresh = AuthService(db).issue_tokens(user)
    csrf = set_auth_cookies(response, access, refresh)
    return LoginResponse(user=UserPublic.model_validate(user), csrf_token=csrf)


@router.post("/{invitation_id}/revoke", response_model=MessageResponse)
async def revoke_invitation(
    invitation_id: int, request: Request,
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await InvitationService(db).revoke(invitation_id, actor=admin, request=request)
    return MessageResponse(message="Invitation revoked")
