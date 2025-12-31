"""File attachment handling service."""

import uuid
import mimetypes
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from todotracker.config import get_settings
from todotracker.models import Attachment, Todo


class FileService:
    """Service for file attachment operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    def _get_storage_path(self, filename: str) -> Path:
        """Get the full path for storing a file."""
        return self.settings.attachments_dir / filename

    async def save_attachment(
        self,
        todo_id: str,
        file_content: bytes,
        original_name: str,
        mime_type: str | None = None,
    ) -> Attachment | None:
        """Save a file attachment for a todo."""
        # Verify todo exists
        todo_result = await self.db.execute(
            select(Todo).where(Todo.id == todo_id)
        )
        if not todo_result.scalar_one_or_none():
            return None

        # Generate unique filename
        file_ext = Path(original_name).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        # Determine mime type
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(original_name)
            mime_type = mime_type or "application/octet-stream"

        # Save file to disk
        file_path = self._get_storage_path(unique_filename)
        file_path.write_bytes(file_content)

        # Create database record
        attachment = Attachment(
            todo_id=todo_id,
            filename=unique_filename,
            original_name=original_name,
            mime_type=mime_type,
            size_bytes=len(file_content),
        )
        self.db.add(attachment)
        await self.db.flush()

        return attachment

    async def get_attachment(self, attachment_id: str) -> tuple[Attachment, bytes] | None:
        """Get an attachment and its file content."""
        result = await self.db.execute(
            select(Attachment).where(Attachment.id == attachment_id)
        )
        attachment = result.scalar_one_or_none()
        if not attachment:
            return None

        file_path = self._get_storage_path(attachment.filename)
        if not file_path.exists():
            return None

        return attachment, file_path.read_bytes()

    async def delete_attachment(self, attachment_id: str) -> bool:
        """Delete an attachment and its file."""
        result = await self.db.execute(
            select(Attachment).where(Attachment.id == attachment_id)
        )
        attachment = result.scalar_one_or_none()
        if not attachment:
            return False

        # Delete file from disk
        file_path = self._get_storage_path(attachment.filename)
        if file_path.exists():
            file_path.unlink()

        # Delete database record
        await self.db.delete(attachment)
        return True

    async def get_attachments_for_todo(self, todo_id: str) -> list[Attachment]:
        """Get all attachments for a todo."""
        result = await self.db.execute(
            select(Attachment)
            .where(Attachment.todo_id == todo_id)
            .order_by(Attachment.uploaded_at)
        )
        return list(result.scalars())
