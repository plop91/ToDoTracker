"""Business logic for todo operations."""

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from todotracker.models import Todo, Tag, Category, PriorityLevel
from todotracker.schemas.todo import TodoCreate, TodoUpdate


class TodoService:
    """Service for todo CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        *,
        category_id: str | None = None,
        tag_id: str | None = None,
        priority_min: int | None = None,
        priority_max: int | None = None,
        completed: bool | None = None,
        due_before: datetime | None = None,
        due_after: datetime | None = None,
        parent_id: str | None = None,
        include_subtasks: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Todo], int]:
        """Get todos with filtering and pagination."""
        # Base query for root todos (no parent) unless parent_id specified
        query = select(Todo).options(
            selectinload(Todo.category),
            selectinload(Todo.tags),
            selectinload(Todo.attachments),
            selectinload(Todo.subtasks).selectinload(Todo.category),
            selectinload(Todo.subtasks).selectinload(Todo.tags),
            selectinload(Todo.subtasks).selectinload(Todo.attachments),
            selectinload(Todo.subtasks).selectinload(Todo.subtasks),
        )

        # Filter by parent
        if parent_id is not None:
            query = query.where(Todo.parent_id == parent_id)
        else:
            # By default, only get root-level todos
            query = query.where(Todo.parent_id.is_(None))

        # Apply filters
        if category_id:
            query = query.where(Todo.category_id == category_id)
        if priority_min is not None:
            query = query.where(Todo.priority >= priority_min)
        if priority_max is not None:
            query = query.where(Todo.priority <= priority_max)
        if completed is not None:
            query = query.where(Todo.completed == completed)
        if due_before:
            query = query.where(Todo.due_date <= due_before)
        if due_after:
            query = query.where(Todo.due_date >= due_after)
        if tag_id:
            query = query.join(Todo.tags).where(Tag.id == tag_id)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate and order
        query = (
            query.order_by(Todo.priority.desc(), Todo.due_date.asc().nullslast())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        return list(result.scalars().unique()), total

    async def get_by_id(self, todo_id: str) -> Todo | None:
        """Get a single todo by ID with all relationships."""
        query = (
            select(Todo)
            .options(
                selectinload(Todo.category),
                selectinload(Todo.tags),
                selectinload(Todo.attachments),
                selectinload(Todo.subtasks).selectinload(Todo.subtasks),
            )
            .where(Todo.id == todo_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: TodoCreate) -> Todo:
        """Create a new todo."""
        # Get tags if specified
        tags = []
        if data.tag_ids:
            tag_query = select(Tag).where(Tag.id.in_(data.tag_ids))
            result = await self.db.execute(tag_query)
            tags = list(result.scalars())

        todo = Todo(
            title=data.title,
            description=data.description,
            due_date=data.due_date,
            priority=data.priority,
            parent_id=data.parent_id,
            category_id=data.category_id,
            tags=tags,
        )
        self.db.add(todo)
        await self.db.flush()

        # Reload with all relationships
        return await self.get_by_id(todo.id)

    async def update(self, todo_id: str, data: TodoUpdate) -> Todo | None:
        """Update a todo."""
        todo = await self.get_by_id(todo_id)
        if not todo:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle tags separately
        if "tag_ids" in update_data:
            tag_ids = update_data.pop("tag_ids")
            if tag_ids is not None:
                tag_query = select(Tag).where(Tag.id.in_(tag_ids))
                result = await self.db.execute(tag_query)
                todo.tags = list(result.scalars())

        # Handle completion status
        if "completed" in update_data:
            if update_data["completed"]:
                todo.mark_complete()
            else:
                todo.mark_incomplete()
            del update_data["completed"]

        # Apply remaining updates
        for key, value in update_data.items():
            setattr(todo, key, value)

        todo.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        # Reload with all relationships
        return await self.get_by_id(todo_id)

    async def delete(self, todo_id: str) -> bool:
        """Delete a todo and its subtasks."""
        todo = await self.get_by_id(todo_id)
        if not todo:
            return False
        await self.db.delete(todo)
        return True

    async def mark_complete(self, todo_id: str) -> Todo | None:
        """Mark a todo as complete."""
        todo = await self.get_by_id(todo_id)
        if not todo:
            return None
        todo.mark_complete()
        await self.db.flush()
        return await self.get_by_id(todo_id)

    async def add_subtask(self, parent_id: str, data: TodoCreate) -> Todo | None:
        """Add a subtask to an existing todo."""
        parent = await self.get_by_id(parent_id)
        if not parent:
            return None

        data.parent_id = parent_id
        return await self.create(data)


class CategoryService:
    """Service for category operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[Category]:
        """Get all categories."""
        result = await self.db.execute(
            select(Category).order_by(Category.name)
        )
        return list(result.scalars())

    async def get_by_id(self, category_id: str) -> Category | None:
        """Get a category by ID."""
        result = await self.db.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, color: str | None = None, icon: str | None = None) -> Category:
        """Create a new category."""
        category = Category(name=name, color=color, icon=icon)
        self.db.add(category)
        await self.db.flush()
        return category

    async def update(self, category_id: str, **kwargs) -> Category | None:
        """Update a category."""
        category = await self.get_by_id(category_id)
        if not category:
            return None
        for key, value in kwargs.items():
            if hasattr(category, key) and value is not None:
                setattr(category, key, value)
        await self.db.flush()
        return category

    async def delete(self, category_id: str) -> bool:
        """Delete a category."""
        category = await self.get_by_id(category_id)
        if not category:
            return False
        await self.db.delete(category)
        return True


class TagService:
    """Service for tag operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[Tag]:
        """Get all tags."""
        result = await self.db.execute(select(Tag).order_by(Tag.name))
        return list(result.scalars())

    async def get_by_id(self, tag_id: str) -> Tag | None:
        """Get a tag by ID."""
        result = await self.db.execute(
            select(Tag).where(Tag.id == tag_id)
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, color: str | None = None) -> Tag:
        """Create a new tag."""
        tag = Tag(name=name, color=color)
        self.db.add(tag)
        await self.db.flush()
        return tag

    async def delete(self, tag_id: str) -> bool:
        """Delete a tag."""
        tag = await self.get_by_id(tag_id)
        if not tag:
            return False
        await self.db.delete(tag)
        return True


class PriorityService:
    """Service for priority level operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[PriorityLevel]:
        """Get all priority levels."""
        result = await self.db.execute(
            select(PriorityLevel).order_by(PriorityLevel.level)
        )
        return list(result.scalars())

    async def get_by_level(self, level: int) -> PriorityLevel | None:
        """Get a priority level by its number."""
        result = await self.db.execute(
            select(PriorityLevel).where(PriorityLevel.level == level)
        )
        return result.scalar_one_or_none()

    async def update(self, level: int, name: str | None = None, color: str | None = None) -> PriorityLevel | None:
        """Update a priority level's name or color."""
        priority = await self.get_by_level(level)
        if not priority:
            return None
        if name is not None:
            priority.name = name
        if color is not None:
            priority.color = color
        await self.db.flush()
        return priority

    async def seed_defaults(self) -> None:
        """Seed default priority levels if none exist."""
        existing = await self.get_all()
        if not existing:
            for priority in PriorityLevel.get_defaults():
                self.db.add(priority)
            await self.db.flush()
