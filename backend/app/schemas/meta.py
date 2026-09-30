from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.enums import StatusCategory


class StatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    name: str
    category: StatusCategory
    order_index: int
    color: str


class TypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    name: str
    icon: str
    color: str


class PriorityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    name: str
    rank: int
    color: str


class MetaOut(BaseModel):
    statuses: list[StatusOut]
    types: list[TypeOut]
    priorities: list[PriorityOut]
