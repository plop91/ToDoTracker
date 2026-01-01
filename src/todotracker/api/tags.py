"""Tag API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from todotracker.database import get_db
from todotracker.schemas.tag import TagCreate, TagUpdate, TagResponse, TagListResponse
from todotracker.services.todo_service import TagService

router = APIRouter(prefix="/tags", tags=["tags"])


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
async def create_tag(
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
    update_data = data.model_dump(exclude_unset=True)
    tag = await service.update(tag_id, **update_data)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    return TagResponse.model_validate(tag)


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: str,
    data: TagUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a tag (full update)."""
    return await _update_tag_impl(tag_id, data, db)


@router.patch("/{tag_id}", response_model=TagResponse)
async def patch_tag(
    tag_id: str,
    data: TagUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partially update a tag (only specified fields are modified)."""
    return await _update_tag_impl(tag_id, data, db)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
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
