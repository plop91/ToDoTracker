"""Tests for service layer."""

import pytest
from datetime import datetime, timezone

from todotracker.services.todo_service import (
    TodoService,
    CategoryService,
    TagService,
    PriorityService,
)
from todotracker.schemas.todo import TodoCreate, TodoUpdate


class TestTodoService:
    """Tests for TodoService."""

    @pytest.mark.asyncio
    async def test_create_todo(self, test_session):
        """Test creating a todo via service."""
        service = TodoService(test_session)
        todo_data = TodoCreate(title="Service test", priority=6)

        todo = await service.create(todo_data)

        assert todo is not None
        assert todo.title == "Service test"
        assert todo.priority == 6

    @pytest.mark.asyncio
    async def test_get_all_todos(self, test_session):
        """Test getting all todos."""
        service = TodoService(test_session)

        # Create some todos
        await service.create(TodoCreate(title="Todo 1"))
        await service.create(TodoCreate(title="Todo 2"))

        todos, total = await service.get_all()

        assert total >= 2
        assert len(todos) >= 2

    @pytest.mark.asyncio
    async def test_get_todo_by_id(self, test_session):
        """Test getting a todo by ID."""
        service = TodoService(test_session)
        created = await service.create(TodoCreate(title="Find me"))

        found = await service.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.title == "Find me"

    @pytest.mark.asyncio
    async def test_update_todo(self, test_session):
        """Test updating a todo."""
        service = TodoService(test_session)
        todo = await service.create(TodoCreate(title="Original"))

        updated = await service.update(
            todo.id,
            TodoUpdate(title="Updated", priority=9)
        )

        assert updated.title == "Updated"
        assert updated.priority == 9

    @pytest.mark.asyncio
    async def test_delete_todo(self, test_session):
        """Test deleting a todo."""
        service = TodoService(test_session)
        todo = await service.create(TodoCreate(title="Delete me"))

        result = await service.delete(todo.id)
        assert result is True

        found = await service.get_by_id(todo.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_mark_complete(self, test_session):
        """Test marking a todo as complete."""
        service = TodoService(test_session)
        todo = await service.create(TodoCreate(title="Complete me"))

        completed = await service.mark_complete(todo.id)

        assert completed.completed is True
        assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_add_subtask(self, test_session):
        """Test adding a subtask."""
        service = TodoService(test_session)
        parent = await service.create(TodoCreate(title="Parent"))

        subtask = await service.add_subtask(
            parent.id,
            TodoCreate(title="Subtask")
        )

        assert subtask.parent_id == parent.id
        assert subtask.title == "Subtask"

    @pytest.mark.asyncio
    async def test_filter_by_priority(self, test_session):
        """Test filtering todos by priority."""
        service = TodoService(test_session)
        await service.create(TodoCreate(title="Low", priority=2))
        await service.create(TodoCreate(title="High", priority=8))

        todos, _ = await service.get_all(priority_min=7)
        assert all(t.priority >= 7 for t in todos)

    @pytest.mark.asyncio
    async def test_filter_by_completed(self, test_session):
        """Test filtering todos by completion status."""
        service = TodoService(test_session)
        todo1 = await service.create(TodoCreate(title="Incomplete"))
        todo2 = await service.create(TodoCreate(title="Complete"))
        await service.mark_complete(todo2.id)

        incomplete, _ = await service.get_all(completed=False)
        complete, _ = await service.get_all(completed=True)

        assert all(not t.completed for t in incomplete)
        assert all(t.completed for t in complete)


class TestCategoryService:
    """Tests for CategoryService."""

    @pytest.mark.asyncio
    async def test_create_category(self, test_session):
        """Test creating a category."""
        service = CategoryService(test_session)

        category = await service.create("Work", color="#0000FF")

        assert category.name == "Work"
        assert category.color == "#0000FF"

    @pytest.mark.asyncio
    async def test_get_all_categories(self, test_session):
        """Test getting all categories."""
        service = CategoryService(test_session)
        await service.create("Cat1")
        await service.create("Cat2")

        categories = await service.get_all()

        assert len(categories) >= 2

    @pytest.mark.asyncio
    async def test_update_category(self, test_session):
        """Test updating a category."""
        service = CategoryService(test_session)
        category = await service.create("Original")

        updated = await service.update(category.id, name="Updated")

        assert updated.name == "Updated"

    @pytest.mark.asyncio
    async def test_delete_category(self, test_session):
        """Test deleting a category."""
        service = CategoryService(test_session)
        category = await service.create("ToDelete")

        result = await service.delete(category.id)

        assert result is True


class TestTagService:
    """Tests for TagService."""

    @pytest.mark.asyncio
    async def test_create_tag(self, test_session):
        """Test creating a tag."""
        service = TagService(test_session)

        tag = await service.create("urgent", color="#FF0000")

        assert tag.name == "urgent"
        assert tag.color == "#FF0000"

    @pytest.mark.asyncio
    async def test_get_all_tags(self, test_session):
        """Test getting all tags."""
        service = TagService(test_session)
        await service.create("tag1")
        await service.create("tag2")

        tags = await service.get_all()

        assert len(tags) >= 2

    @pytest.mark.asyncio
    async def test_delete_tag(self, test_session):
        """Test deleting a tag."""
        service = TagService(test_session)
        tag = await service.create("todelete")

        result = await service.delete(tag.id)

        assert result is True


class TestPriorityService:
    """Tests for PriorityService."""

    @pytest.mark.asyncio
    async def test_get_all_priorities(self, test_session):
        """Test getting all priority levels."""
        service = PriorityService(test_session)

        priorities = await service.get_all()

        assert len(priorities) == 10

    @pytest.mark.asyncio
    async def test_get_priority_by_level(self, test_session):
        """Test getting a priority by level."""
        service = PriorityService(test_session)

        priority = await service.get_by_level(5)

        assert priority is not None
        assert priority.level == 5
        assert priority.name == "Normal"

    @pytest.mark.asyncio
    async def test_update_priority(self, test_session):
        """Test updating a priority level."""
        service = PriorityService(test_session)

        updated = await service.update(5, name="Medium")

        assert updated.name == "Medium"
