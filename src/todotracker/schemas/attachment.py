"""Attachment schemas."""

from datetime import datetime

from todotracker.schemas.base import BaseSchema


class AttachmentResponse(BaseSchema):
    """Schema for attachment responses."""

    id: str
    todo_id: str
    filename: str
    original_name: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
