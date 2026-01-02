"""Todo API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from todotracker.config import get_settings
from todotracker.database import get_db
from todotracker.schemas.todo import (
    TodoCreate,
    TodoUpdate,
    TodoResponse,
    TodoListResponse,
)
from todotracker.services.todo_service import TodoService, TodoValidationError

router = APIRouter(prefix="/todos", tags=["todos"])

# Rate limiter for this module
limiter = Limiter(key_func=get_remote_address)


def _get_default_rate_limit() -> str:
    """Get the default rate limit from settings."""
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return "1000000/minute"  # Effectively unlimited when disabled
    return settings.rate_limit_default


@router.get("", response_model=TodoListResponse)
async def list_todos(
    category_id: str | None = None,
    tag_id: str | None = None,
    priority_min: int | None = None,
    priority_max: int | None = None,
    completed: bool | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List todos with optional filtering."""
    service = TodoService(db)
    todos, total = await service.get_all(
        category_id=category_id,
        tag_id=tag_id,
        priority_min=priority_min,
        priority_max=priority_max,
        completed=completed,
        due_before=due_before,
        due_after=due_after,
        page=page,
        page_size=page_size,
    )
    return TodoListResponse(
        items=[TodoResponse.model_validate(t) for t in todos],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(_get_default_rate_limit)
async def create_todo(
    request: Request,
    data: TodoCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new todo."""
    service = TodoService(db)
    try:
        todo = await service.create(data)
    except TodoValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    return TodoResponse.model_validate(todo)


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single todo by ID."""
    service = TodoService(db)
    todo = await service.get_by_id(todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    return TodoResponse.model_validate(todo)


async def _update_todo_impl(
    todo_id: str,
    data: TodoUpdate,
    db: AsyncSession,
) -> TodoResponse:
    """Shared implementation for PUT and PATCH todo updates."""
    service = TodoService(db)
    try:
        todo = await service.update(todo_id, data)
    except TodoValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    return TodoResponse.model_validate(todo)


@router.put("/{todo_id}", response_model=TodoResponse)
@limiter.limit(_get_default_rate_limit)
async def update_todo(
    request: Request,
    todo_id: str,
    data: TodoUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a todo (full update)."""
    return await _update_todo_impl(todo_id, data, db)


@router.patch("/{todo_id}", response_model=TodoResponse)
@limiter.limit(_get_default_rate_limit)
async def patch_todo(
    request: Request,
    todo_id: str,
    data: TodoUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partially update a todo (only specified fields are modified)."""
    return await _update_todo_impl(todo_id, data, db)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(_get_default_rate_limit)
async def delete_todo(
    request: Request,
    todo_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a todo and its subtasks."""
    service = TodoService(db)
    deleted = await service.delete(todo_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )


@router.post("/{todo_id}/complete", response_model=TodoResponse)
@limiter.limit(_get_default_rate_limit)
async def complete_todo(
    request: Request,
    todo_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark a todo as complete."""
    service = TodoService(db)
    todo = await service.mark_complete(todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    return TodoResponse.model_validate(todo)


@router.post("/{todo_id}/subtasks", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(_get_default_rate_limit)
async def create_subtask(
    request: Request,
    todo_id: str,
    data: TodoCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a subtask to an existing todo."""
    service = TodoService(db)
    try:
        subtask = await service.add_subtask(todo_id, data)
    except TodoValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    if not subtask:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent todo not found",
        )
    return TodoResponse.model_validate(subtask)
