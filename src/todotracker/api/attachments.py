"""Attachment API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from todotracker.config import get_settings
from todotracker.database import get_db
from todotracker.schemas.attachment import AttachmentResponse
from todotracker.services.file_service import FileService, FileValidationError

router = APIRouter(tags=["attachments"])


@router.post(
    "/todos/{todo_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    todo_id: str,
    file: UploadFile,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Upload a file attachment for a todo."""
    settings = get_settings()

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Check Content-Length header for early rejection of oversized files
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
            pass  # Invalid content-length header, continue with normal validation

    content = await file.read()
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
    return Response(
        content=content,
        media_type=attachment.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{attachment.original_name}"'
        },
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
