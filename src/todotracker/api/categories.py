"""Category API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from todotracker.config import get_settings
from todotracker.database import get_db
from todotracker.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
)
from todotracker.services.todo_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])

# Rate limiter for this module
limiter = Limiter(key_func=get_remote_address)


def _get_default_rate_limit() -> str:
    """Get the default rate limit from settings."""
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return "1000000/minute"  # Effectively unlimited when disabled
    return settings.rate_limit_default


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    db: AsyncSession = Depends(get_db),
):
    """List all categories."""
    service = CategoryService(db)
    categories = await service.get_all()
    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in categories],
        total=len(categories),
    )


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(_get_default_rate_limit)
async def create_category(
    request: Request,
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new category."""
    service = CategoryService(db)
    category = await service.create(
        name=data.name,
        color=data.color,
        icon=data.icon,
    )
    return CategoryResponse.model_validate(category)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a category by ID."""
    service = CategoryService(db)
    category = await service.get_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return CategoryResponse.model_validate(category)


async def _update_category_impl(
    category_id: str,
    data: CategoryUpdate,
    db: AsyncSession,
) -> CategoryResponse:
    """Shared implementation for PUT and PATCH category updates."""
    service = CategoryService(db)
    # Extract only the fields that were explicitly set in the request
    update_data = data.model_dump(exclude_unset=True)
    category = await service.update(
        category_id,
        name=update_data.get("name"),
        color=update_data.get("color"),
        icon=update_data.get("icon"),
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return CategoryResponse.model_validate(category)


@router.put("/{category_id}", response_model=CategoryResponse)
@limiter.limit(_get_default_rate_limit)
async def update_category(
    request: Request,
    category_id: str,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a category (full update)."""
    return await _update_category_impl(category_id, data, db)


@router.patch("/{category_id}", response_model=CategoryResponse)
@limiter.limit(_get_default_rate_limit)
async def patch_category(
    request: Request,
    category_id: str,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partially update a category (only specified fields are modified)."""
    return await _update_category_impl(category_id, data, db)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(_get_default_rate_limit)
async def delete_category(
    request: Request,
    category_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a category."""
    service = CategoryService(db)
    deleted = await service.delete(category_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
