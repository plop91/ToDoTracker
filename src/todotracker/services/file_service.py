"""File attachment handling service."""

import uuid
import mimetypes
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from todotracker.config import get_settings
from todotracker.models import Attachment, Todo


class FileValidationError(Exception):
    """Raised when file validation fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# Magic bytes for common file types (first few bytes of file)
# Special cases: .tar has signature at offset 257, .webp needs RIFF at 0 AND WEBP at 8
MAGIC_BYTES = {
    # Images
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".gif": [b"GIF87a", b"GIF89a"],
    ".bmp": [b"BM"],
    ".webp": [b"RIFF"],  # Also requires "WEBP" at offset 8 (checked separately)
    ".ico": [b"\x00\x00\x01\x00", b"\x00\x00\x02\x00"],
    # Documents
    ".pdf": [b"%PDF"],
    ".doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],  # OLE compound
    ".docx": [b"PK\x03\x04"],  # ZIP-based
    ".xls": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    ".xlsx": [b"PK\x03\x04"],
    ".ppt": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    ".pptx": [b"PK\x03\x04"],
    ".odt": [b"PK\x03\x04"],
    ".ods": [b"PK\x03\x04"],
    ".odp": [b"PK\x03\x04"],
    ".rtf": [b"{\\rtf"],
    # Archives
    ".zip": [b"PK\x03\x04", b"PK\x05\x06"],
    ".7z": [b"7z\xbc\xaf\x27\x1c"],
    ".rar": [b"Rar!\x1a\x07"],
    ".gz": [b"\x1f\x8b"],
    ".tar": [b"ustar"],  # At offset 257
}

# Extensions that don't need magic byte validation (text-based)
# Note: .svg excluded from allowed extensions due to XSS risk
TEXT_EXTENSIONS = {
    ".txt", ".csv", ".json", ".xml", ".yaml", ".yml",
    ".md", ".html", ".css",
}


class FileService:
    """Service for file attachment operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    def _get_storage_path(self, filename: str) -> Path:
        """Get the full path for storing a file."""
        return self.settings.attachments_dir / filename

    def _sanitize_filename(self, filename: str) -> str:
        """Extract just the filename, removing any path components.

        Handles both Unix and Windows path separators to prevent
        path traversal attacks like '../../../etc/passwd'.
        """
        # Extract basename using both path types to handle cross-platform uploads
        name = PurePosixPath(filename).name
        name = PureWindowsPath(name).name

        # Remove any remaining dangerous characters
        name = re.sub(r'[<>:"|?*\x00-\x1f]', '_', name)

        # Ensure we have a valid filename
        if not name or name in (".", ".."):
            raise FileValidationError("Invalid filename")

        return name

    def _validate_extension(self, filename: str) -> str:
        """Validate file extension is allowed. Returns lowercase extension."""
        ext = Path(filename).suffix.lower()

        if not ext:
            raise FileValidationError("File must have an extension")

        if ext not in self.settings.allowed_file_extensions:
            allowed = ", ".join(sorted(self.settings.allowed_file_extensions))
            raise FileValidationError(
                f"File type '{ext}' is not allowed. Allowed types: {allowed}"
            )

        return ext

    def _validate_content(self, content: bytes, extension: str) -> None:
        """Validate file content matches the claimed extension using magic bytes."""
        # Skip validation for text-based files
        if extension in TEXT_EXTENSIONS:
            return

        # Check magic bytes if we have a signature for this extension
        if extension in MAGIC_BYTES:
            signatures = MAGIC_BYTES[extension]
            matched = False

            for sig in signatures:
                # Special case for tar files (signature at offset 257)
                if extension == ".tar":
                    if len(content) >= 262 and content[257:262] == sig:
                        matched = True
                        break
                # Special case for webp: needs RIFF at start AND "WEBP" at offset 8
                elif extension == ".webp":
                    if (len(content) >= 12 and
                            content.startswith(sig) and
                            content[8:12] == b"WEBP"):
                        matched = True
                        break
                else:
                    if content.startswith(sig):
                        matched = True
                        break

            if not matched:
                raise FileValidationError(
                    f"File content does not match the '{extension}' file type"
                )

    def _validate_size(self, content: bytes) -> None:
        """Validate file size is within limits."""
        if len(content) > self.settings.max_upload_size_bytes:
            max_mb = self.settings.max_upload_size_bytes / (1024 * 1024)
            raise FileValidationError(
                f"File size exceeds maximum allowed size of {max_mb:.1f} MB"
            )

    async def save_attachment(
        self,
        todo_id: str,
        file_content: bytes,
        original_name: str,
        mime_type: str | None = None,
    ) -> Attachment | None:
        """Save a file attachment for a todo.

        Uses a two-phase approach to prevent file orphaning:
        1. Create database record first (can be rolled back)
        2. Write file to disk only after successful flush
        3. Register cleanup handler for rollback scenarios

        Raises:
            FileValidationError: If file validation fails (size, type, content).

        Returns:
            Attachment if successful, None if todo not found.
        """
        # Validate file size first (before any other processing)
        self._validate_size(file_content)

        # Sanitize filename to prevent path traversal
        safe_name = self._sanitize_filename(original_name)

        # Validate file extension
        file_ext = self._validate_extension(safe_name)

        # Validate content matches the claimed file type
        self._validate_content(file_content, file_ext)

        # Verify todo exists
        todo_result = await self.db.execute(
            select(Todo).where(Todo.id == todo_id)
        )
        if not todo_result.scalar_one_or_none():
            return None

        # Generate unique filename with validated extension
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        # Determine mime type from sanitized filename
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(safe_name)
            mime_type = mime_type or "application/octet-stream"

        file_path = self._get_storage_path(unique_filename)

        # Create database record FIRST (before writing file)
        # This way, if commit fails, no file is orphaned
        attachment = Attachment(
            todo_id=todo_id,
            filename=unique_filename,
            original_name=safe_name,  # Store sanitized name
            mime_type=mime_type,
            size_bytes=len(file_content),
        )
        self.db.add(attachment)
        await self.db.flush()

        # Now write file to disk - if this fails, the DB transaction
        # will be rolled back by the caller's error handling
        try:
            file_path.write_bytes(file_content)
        except Exception:
            # If file write fails, we need to remove the DB record
            # The expunge removes it from the session without hitting the DB
            await self.db.delete(attachment)
            await self.db.flush()
            raise

        # Store file path on attachment for potential rollback cleanup
        # This is used by the get_db dependency's rollback handler
        attachment._pending_file_path = file_path  # type: ignore[attr-defined]

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
