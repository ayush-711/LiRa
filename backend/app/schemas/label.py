from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LabelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    color: str
    description: str | None = None
    is_archived: bool = False


class LabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field("#6366f1", max_length=20)
    description: str | None = Field(None, max_length=255)


class LabelUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=60)
    color: str | None = Field(None, max_length=20)
    description: str | None = Field(None, max_length=255)
    is_archived: bool | None = None
