"""Business logic for todo operations."""

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from todotracker.config import get_settings
from todotracker.models import Todo, Tag, Category, PriorityLevel
from todotracker.schemas.todo import TodoCreate, TodoUpdate


class TodoValidationError(Exception):
    """Raised when todo validation fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _build_subtask_loader(depth: int):
    """Build nested selectinload chain for subtasks up to specified depth.

    Args:
        depth: Maximum nesting depth to load (e.g., 5 loads 5 levels of subtasks)

    Returns:
        A selectinload chain that eager-loads subtasks to the specified depth.
    """
    if depth <= 0:
        return None

    # Start with the innermost level and work outward
    loader = selectinload(Todo.subtasks)
    for _ in range(depth - 1):
        loader = selectinload(Todo.subtasks).options(
            loader,
            selectinload(Todo.category),
            selectinload(Todo.tags),
            selectinload(Todo.attachments),
        )
    return loader


class TodoService:
    """Service for todo CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    def _get_subtask_load_options(self):
        """Get SQLAlchemy load options for subtasks based on max depth setting."""
        depth = self.settings.max_subtask_depth
        options = [
            selectinload(Todo.category),
            selectinload(Todo.tags),
            selectinload(Todo.attachments),
        ]

        # Build nested subtask loader for full depth
        if depth > 0:
            loader = _build_subtask_loader(depth)
            if loader:
                options.append(loader)

        return options

    async def _get_parent_depth(self, parent_id: str) -> int:
        """Calculate the depth of a todo in the hierarchy.

        Returns the number of ancestors (0 for root-level todos, 1 for children of root, etc.).
        """
        depth = 0
        current_id = parent_id
        iterations = 0

        while True:
            result = await self.db.execute(
                select(Todo.parent_id).where(Todo.id == current_id)
            )
            row = result.first()
            if row is None:
                # Todo not found
                break

            next_parent = row[0]
            if next_parent is None:
                # Reached root level, stop counting
                break

            depth += 1
            current_id = next_parent
            iterations += 1

            # Safety check to prevent infinite loops (shouldn't happen with proper validation)
            if iterations > self.settings.max_subtask_depth + 10:
                raise TodoValidationError("Circular reference detected in todo hierarchy")

        return depth

    async def _would_create_cycle(self, todo_id: str, new_parent_id: str) -> bool:
        """Check if setting new_parent_id as the parent would create a cycle.

        A cycle would occur if new_parent_id is the todo itself or one of its descendants.
        """
        if todo_id == new_parent_id:
            return True

        # Walk up from new_parent_id to check if we ever hit todo_id
        current_id = new_parent_id
        visited = {todo_id}  # The todo we're moving

        while current_id is not None:
            if current_id in visited:
                return True
            visited.add(current_id)

            result = await self.db.execute(
                select(Todo.parent_id).where(Todo.id == current_id)
            )
            row = result.first()
            if row is None:
                break
            current_id = row[0]

        # Also check descendants of todo_id to ensure new_parent_id isn't among them
        descendants = await self._get_all_descendant_ids(todo_id)
        return new_parent_id in descendants

    async def _get_all_descendant_ids(self, todo_id: str) -> set[str]:
        """Get all descendant IDs of a todo (children, grandchildren, etc.)."""
        descendants = set()
        to_visit = [todo_id]

        while to_visit:
            current_id = to_visit.pop()
            result = await self.db.execute(
                select(Todo.id).where(Todo.parent_id == current_id)
            )
            for row in result:
                child_id = row[0]
                if child_id not in descendants:
                    descendants.add(child_id)
                    to_visit.append(child_id)

        return descendants

    async def _validate_parent(self, parent_id: str | None, todo_id: str | None = None) -> None:
        """Validate parent assignment for depth and circular reference constraints.

        Args:
            parent_id: The proposed parent ID
            todo_id: The ID of the todo being updated (None for new todos)

        Raises:
            TodoValidationError: If validation fails
        """
        if parent_id is None:
            return

        # Check parent exists
        result = await self.db.execute(
            select(Todo.id).where(Todo.id == parent_id)
        )
        if result.first() is None:
            raise TodoValidationError(f"Parent todo '{parent_id}' not found")

        # Check for circular reference (only for updates)
        if todo_id is not None:
            if await self._would_create_cycle(todo_id, parent_id):
                raise TodoValidationError(
                    "Cannot set parent: this would create a circular reference"
                )

        # Check depth limit
        parent_depth = await self._get_parent_depth(parent_id)
        new_depth = parent_depth + 1  # The new todo/subtask will be one level deeper

        if new_depth > self.settings.max_subtask_depth:
            raise TodoValidationError(
                f"Maximum subtask depth of {self.settings.max_subtask_depth} exceeded. "
                f"Parent is already at depth {parent_depth}."
            )

    async def _validate_and_get_tags(self, tag_ids: list[str]) -> list[Tag]:
        """Validate that all tag IDs exist and return the Tag objects.

        Args:
            tag_ids: List of tag IDs to validate.

        Returns:
            List of Tag objects.

        Raises:
            TodoValidationError: If any tag IDs don't exist.
        """
        if not tag_ids:
            return []

        tag_query = select(Tag).where(Tag.id.in_(tag_ids))
        result = await self.db.execute(tag_query)
        tags = list(result.scalars())

        # Check if all requested tags were found
        found_ids = {tag.id for tag in tags}
        missing_ids = set(tag_ids) - found_ids
        if missing_ids:
            raise TodoValidationError(
                f"Tag(s) not found: {', '.join(sorted(missing_ids))}"
            )

        return tags

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
        # Load subtasks to full configured depth (default 5 levels)
        query = select(Todo).options(*self._get_subtask_load_options())

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
        # Load subtasks to full configured depth (default 5 levels)
        query = (
            select(Todo)
            .options(*self._get_subtask_load_options())
            .where(Todo.id == todo_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: TodoCreate) -> Todo:
        """Create a new todo.

        Raises:
            TodoValidationError: If parent validation fails (depth limit or not found),
                or if any tag IDs don't exist.
        """
        # Validate parent if specified
        await self._validate_parent(data.parent_id)

        # Validate and get tags if specified
        tags = await self._validate_and_get_tags(data.tag_ids)

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
        """Update a todo.

        Raises:
            TodoValidationError: If parent validation fails (circular ref or depth limit),
                or if any tag IDs don't exist.
        """
        todo = await self.get_by_id(todo_id)
        if not todo:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Validate parent_id change if specified
        if "parent_id" in update_data:
            new_parent_id = update_data["parent_id"]
            # Only validate if it's actually changing
            if new_parent_id != todo.parent_id:
                await self._validate_parent(new_parent_id, todo_id=todo_id)

        # Handle tags separately - validate all exist before applying
        if "tag_ids" in update_data:
            tag_ids = update_data.pop("tag_ids")
            if tag_ids is not None:
                todo.tags = await self._validate_and_get_tags(tag_ids)

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

    async def update(
        self,
        category_id: str,
        *,
        name: str | None = None,
        color: str | None = None,
        icon: str | None = None,
    ) -> Category | None:
        """Update a category.

        Only the explicitly provided fields will be updated.
        Pass None to leave a field unchanged.
        """
        category = await self.get_by_id(category_id)
        if not category:
            return None

        if name is not None:
            category.name = name
        if color is not None:
            category.color = color
        if icon is not None:
            category.icon = icon

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

    async def update(
        self,
        tag_id: str,
        *,
        name: str | None = None,
        color: str | None = None,
    ) -> Tag | None:
        """Update a tag.

        Only the explicitly provided fields will be updated.
        Pass None to leave a field unchanged.
        """
        tag = await self.get_by_id(tag_id)
        if not tag:
            return None

        if name is not None:
            tag.name = name
        if color is not None:
            tag.color = color

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
    """Service for priority level operations with caching.

    Priority levels are static data (10 levels, rarely changed) so they
    benefit from in-memory caching to reduce database queries.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        # Import here to avoid circular imports
        from todotracker.services.cache import priority_cache
        self._cache = priority_cache

    async def _fetch_all(self) -> list[PriorityLevel]:
        """Fetch all priority levels from database."""
        result = await self.db.execute(
            select(PriorityLevel).order_by(PriorityLevel.level)
        )
        return list(result.scalars())

    async def get_all(self) -> list[PriorityLevel]:
        """Get all priority levels (cached).

        Returns cached data if available, otherwise fetches from database.
        Cache TTL is 5 minutes by default.
        """
        return await self._cache.get_or_fetch(self._fetch_all)

    async def get_by_level(self, level: int) -> PriorityLevel | None:
        """Get a priority level by its number (uses cache)."""
        priorities = await self.get_all()
        for p in priorities:
            if p.level == level:
                return p
        return None

    async def update(self, level: int, name: str | None = None, color: str | None = None) -> PriorityLevel | None:
        """Update a priority level's name or color.

        Invalidates the cache after update.
        """
        # Fetch directly from DB for update (not from cache)
        result = await self.db.execute(
            select(PriorityLevel).where(PriorityLevel.level == level)
        )
        priority = result.scalar_one_or_none()
        if not priority:
            return None
        if name is not None:
            priority.name = name
        if color is not None:
            priority.color = color
        await self.db.flush()

        # Invalidate cache so next read gets fresh data
        self._cache.invalidate()

        return priority

    async def seed_defaults(self) -> None:
        """Seed default priority levels if none exist."""
        existing = await self._fetch_all()  # Direct fetch, not cached
        if not existing:
            for priority in PriorityLevel.get_defaults():
                self.db.add(priority)
            await self.db.flush()
            # Invalidate cache after seeding
            self._cache.invalidate()
