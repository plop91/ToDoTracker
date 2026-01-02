"""Attachment API endpoints."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from todotracker.config import get_settings
from todotracker.database import get_db
from todotracker.schemas.attachment import AttachmentResponse
from todotracker.services.file_service import FileService, FileValidationError

router = APIRouter(tags=["attachments"])

# Create a limiter for this module - uses same key function as main
limiter = Limiter(key_func=get_remote_address)


def _get_upload_rate_limit() -> str:
    """Get the upload rate limit from settings."""
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return "1000000/minute"  # Effectively unlimited when disabled
    return settings.rate_limit_uploads


@router.post(
    "/todos/{todo_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(_get_upload_rate_limit)
async def upload_attachment(
    todo_id: str,
    file: UploadFile,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Upload a file attachment for a todo.

    Rate limited to prevent abuse (default: 10 uploads/minute).
    """
    settings = get_settings()

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Check Content-Length header for early rejection of oversized files
    # Note: This can be spoofed, so we also validate during streaming read
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            size = int(content_length)
            if size > settings.max_upload_size_bytes:
                max_mb = settings.max_upload_size_bytes / (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size exceeds maximum allowed size of {max_mb:.1f} MB",
                )
        except ValueError:
            pass  # Invalid content-length header, continue with streaming validation

    # Read file in chunks to prevent memory exhaustion from spoofed Content-Length
    # or missing headers. Reject as soon as we exceed the limit.
    max_size = settings.max_upload_size_bytes
    chunk_size = 64 * 1024  # 64 KB chunks
    chunks = []
    total_size = 0

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {max_mb:.1f} MB",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    service = FileService(db)

    try:
        attachment = await service.save_attachment(
            todo_id=todo_id,
            file_content=content,
            original_name=file.filename,
            mime_type=file.content_type,
        )
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )

    return AttachmentResponse.model_validate(attachment)


@router.get("/attachments/{attachment_id}")
async def download_attachment(
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download an attachment file."""
    service = FileService(db)
    result = await service.get_attachment(attachment_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    attachment, content = result

    # RFC 5987 encoding for Content-Disposition to prevent header injection
    # and properly handle non-ASCII characters
    # Use both filename (ASCII fallback) and filename* (UTF-8 encoded) for compatibility
    filename = attachment.original_name

    # Create ASCII-safe fallback by replacing non-ASCII chars
    ascii_filename = filename.encode('ascii', 'replace').decode('ascii').replace('?', '_')
    # Remove any characters that could break the header
    ascii_filename = ascii_filename.replace('"', "'").replace('\n', '_').replace('\r', '_')

    # RFC 5987 encoded version for UTF-8 support
    encoded_filename = quote(filename, safe='')

    content_disposition = (
        f"attachment; "
        f'filename="{ascii_filename}"; '
        f"filename*=UTF-8''{encoded_filename}"
    )

    return Response(
        content=content,
        media_type=attachment.mime_type,
        headers={"Content-Disposition": content_disposition},
    )


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete an attachment."""
    service = FileService(db)
    deleted = await service.delete_attachment(attachment_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
