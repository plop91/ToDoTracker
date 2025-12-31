"""Priority level API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from todotracker.database import get_db
from todotracker.schemas.priority import PriorityLevelUpdate, PriorityLevelResponse
from todotracker.services.todo_service import PriorityService

router = APIRouter(prefix="/priorities", tags=["priorities"])


@router.get("", response_model=list[PriorityLevelResponse])
async def list_priorities(
    db: AsyncSession = Depends(get_db),
):
    """List all priority levels."""
    service = PriorityService(db)
    priorities = await service.get_all()
    return [PriorityLevelResponse.model_validate(p) for p in priorities]


@router.put("/{level}", response_model=PriorityLevelResponse)
async def update_priority(
    level: int,
    data: PriorityLevelUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a priority level's name or color."""
    if not 1 <= level <= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Priority level must be between 1 and 10",
        )

    service = PriorityService(db)
    priority = await service.update(level, name=data.name, color=data.color)
    if not priority:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Priority level not found",
        )
    return PriorityLevelResponse.model_validate(priority)
