"""Tag API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from todotracker.config import get_settings
from todotracker.database import get_db
from todotracker.schemas.tag import TagCreate, TagUpdate, TagResponse, TagListResponse
from todotracker.services.todo_service import TagService

router = APIRouter(prefix="/tags", tags=["tags"])

# Rate limiter for this module
limiter = Limiter(key_func=get_remote_address)


def _get_default_rate_limit() -> str:
    """Get the default rate limit from settings."""
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return "1000000/minute"  # Effectively unlimited when disabled
    return settings.rate_limit_default


@router.get("", response_model=TagListResponse)
async def list_tags(
    db: AsyncSession = Depends(get_db),
):
    """List all tags."""
    service = TagService(db)
    tags = await service.get_all()
    return TagListResponse(
        items=[TagResponse.model_validate(t) for t in tags],
        total=len(tags),
    )


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(_get_default_rate_limit)
async def create_tag(
    request: Request,
    data: TagCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new tag."""
    service = TagService(db)
    tag = await service.create(name=data.name, color=data.color)
    return TagResponse.model_validate(tag)


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a tag by ID."""
    service = TagService(db)
    tag = await service.get_by_id(tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    return TagResponse.model_validate(tag)


async def _update_tag_impl(
    tag_id: str,
    data: TagUpdate,
    db: AsyncSession,
) -> TagResponse:
    """Shared implementation for PUT and PATCH tag updates."""
    service = TagService(db)
    # Extract only the fields that were explicitly set in the request
    update_data = data.model_dump(exclude_unset=True)
    tag = await service.update(
        tag_id,
        name=update_data.get("name"),
        color=update_data.get("color"),
    )
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    return TagResponse.model_validate(tag)


@router.put("/{tag_id}", response_model=TagResponse)
@limiter.limit(_get_default_rate_limit)
async def update_tag(
    request: Request,
    tag_id: str,
    data: TagUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a tag (full update)."""
    return await _update_tag_impl(tag_id, data, db)


@router.patch("/{tag_id}", response_model=TagResponse)
@limiter.limit(_get_default_rate_limit)
async def patch_tag(
    request: Request,
    tag_id: str,
    data: TagUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partially update a tag (only specified fields are modified)."""
    return await _update_tag_impl(tag_id, data, db)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(_get_default_rate_limit)
async def delete_tag(
    request: Request,
    tag_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a tag."""
    service = TagService(db)
    deleted = await service.delete(tag_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
