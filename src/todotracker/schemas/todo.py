"""Todo schemas."""

from datetime import datetime

from pydantic import Field

from todotracker.schemas.base import BaseSchema
from todotracker.schemas.category import CategoryResponse
from todotracker.schemas.tag import TagResponse
from todotracker.schemas.attachment import AttachmentResponse


class TodoCreate(BaseSchema):
    """Schema for creating a todo."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    due_date: datetime | None = None
    priority: int = Field(default=5, ge=1, le=10)
    parent_id: str | None = None
    category_id: str | None = None
    tag_ids: list[str] = Field(default_factory=list)


class TodoUpdate(BaseSchema):
    """Schema for updating a todo."""

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    due_date: datetime | None = None
    priority: int | None = Field(None, ge=1, le=10)
    category_id: str | None = None
    tag_ids: list[str] | None = None
    completed: bool | None = None


class TodoResponse(BaseSchema):
    """Schema for todo responses."""

    id: str
    title: str
    description: str | None
    due_date: datetime | None
    priority: int
    completed: bool
    completed_at: datetime | None
    parent_id: str | None
    category_id: str | None
    created_at: datetime
    updated_at: datetime

    # Nested relationships
    category: CategoryResponse | None = None
    tags: list[TagResponse] = Field(default_factory=list)
    attachments: list[AttachmentResponse] = Field(default_factory=list)
    subtasks: list["TodoResponse"] = Field(default_factory=list)


class TodoListResponse(BaseSchema):
    """Schema for paginated todo list responses."""

    items: list[TodoResponse]
    total: int
    page: int = 1
    page_size: int = 50


# Needed for self-referential model
TodoResponse.model_rebuild()
