"""Tag schemas."""

from datetime import datetime

from pydantic import Field

from todotracker.schemas.base import BaseSchema


class TagCreate(BaseSchema):
    """Schema for creating a tag."""

    name: str = Field(..., min_length=1, max_length=50)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagUpdate(BaseSchema):
    """Schema for updating a tag."""

    name: str | None = Field(None, min_length=1, max_length=50)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagResponse(BaseSchema):
    """Schema for tag responses."""

    id: str
    name: str
    color: str | None
    created_at: datetime


class TagListResponse(BaseSchema):
    """Schema for paginated tag list responses."""

    items: list[TagResponse]
    total: int
