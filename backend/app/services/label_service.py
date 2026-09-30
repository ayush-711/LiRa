"""Label management."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import permissions
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.models.label import Label
from app.models.user import User
from app.repositories.label_repo import LabelRepository


class LabelService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = LabelRepository(db)

    async def list(self, *, include_archived: bool = False) -> list[Label]:
        return await self.repo.list(include_archived=include_archived)

    async def create(self, *, actor: User, name: str, color: str,
                     description: str | None) -> Label:
        if not permissions.can_manage_labels(actor):
            raise PermissionDeniedError("You cannot manage labels")
        name = name.strip()
        if not name:
            raise ValidationError("Label name is required", code="NAME_REQUIRED")
        if await self.repo.get_by_name(name):
            raise ConflictError("A label with that name already exists", code="LABEL_EXISTS")
        label = Label(name=name, color=color or "#6366f1",
                      description=description or None, created_by_id=actor.id)
        self.repo.add(label)
        await self.db.commit()
        await self.db.refresh(label)
        return label

    async def update(self, label_id: int, *, actor: User, changes: dict) -> Label:
        if not permissions.can_manage_labels(actor):
            raise PermissionDeniedError("You cannot manage labels")
        label = await self.repo.get(label_id)
        if label is None:
            raise NotFoundError("Label not found", code="LABEL_NOT_FOUND")
        if changes.get("name"):
            name = changes["name"].strip()
            existing = await self.repo.get_by_name(name)
            if existing and existing.id != label.id:
                raise ConflictError("A label with that name already exists", code="LABEL_EXISTS")
            label.name = name
        if "color" in changes and changes["color"]:
            label.color = changes["color"]
        if "description" in changes:
            label.description = changes["description"] or None
        if "is_archived" in changes and changes["is_archived"] is not None:
            label.is_archived = changes["is_archived"]
        await self.db.commit()
        await self.db.refresh(label)
        return label
