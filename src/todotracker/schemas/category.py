"""Category schemas."""

from datetime import datetime

from pydantic import Field

from todotracker.schemas.base import BaseSchema


class CategoryCreate(BaseSchema):
    """Schema for creating a category."""

    name: str = Field(..., min_length=1, max_length=100)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(None, max_length=50)


class CategoryUpdate(BaseSchema):
    """Schema for updating a category."""

    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = None


class CategoryResponse(BaseSchema):
    """Schema for category responses."""

    id: str
    name: str
    color: str | None
    icon: str | None
    created_at: datetime


class CategoryListResponse(BaseSchema):
    """Schema for paginated category list responses."""

    items: list[CategoryResponse]
    total: int
