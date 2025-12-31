"""Tests for database models."""

import pytest
from datetime import datetime, timezone

from todotracker.models import Todo, Category, Tag, PriorityLevel


class TestTodoModel:
    """Tests for the Todo model."""

    @pytest.mark.asyncio
    async def test_create_todo(self, test_session):
        """Test creating a basic todo."""
        todo = Todo(title="Test todo", priority=5)
        test_session.add(todo)
        await test_session.flush()

        assert todo.id is not None
        assert todo.title == "Test todo"
        assert todo.priority == 5
        assert todo.completed is False
        assert todo.created_at is not None

    @pytest.mark.asyncio
    async def test_todo_mark_complete(self, test_session):
        """Test marking a todo as complete."""
        todo = Todo(title="Test todo")
        test_session.add(todo)
        await test_session.flush()

        todo.mark_complete()
        await test_session.flush()

        assert todo.completed is True
        assert todo.completed_at is not None

    @pytest.mark.asyncio
    async def test_todo_mark_incomplete(self, test_session):
        """Test marking a completed todo as incomplete."""
        todo = Todo(title="Test todo")
        todo.mark_complete()
        test_session.add(todo)
        await test_session.flush()

        todo.mark_incomplete()
        await test_session.flush()

        assert todo.completed is False
        assert todo.completed_at is None

    @pytest.mark.asyncio
    async def test_todo_with_category(self, test_session):
        """Test creating a todo with a category."""
        category = Category(name="Work", color="#FF0000")
        test_session.add(category)
        await test_session.flush()

        todo = Todo(title="Work task", category_id=category.id)
        test_session.add(todo)
        await test_session.flush()

        assert todo.category_id == category.id


class TestCategoryModel:
    """Tests for the Category model."""

    @pytest.mark.asyncio
    async def test_create_category(self, test_session):
        """Test creating a category."""
        category = Category(name="Personal", color="#00FF00", icon="home")
        test_session.add(category)
        await test_session.flush()

        assert category.id is not None
        assert category.name == "Personal"
        assert category.color == "#00FF00"
        assert category.icon == "home"


class TestTagModel:
    """Tests for the Tag model."""

    @pytest.mark.asyncio
    async def test_create_tag(self, test_session):
        """Test creating a tag."""
        tag = Tag(name="urgent", color="#FF0000")
        test_session.add(tag)
        await test_session.flush()

        assert tag.id is not None
        assert tag.name == "urgent"
        assert tag.color == "#FF0000"


class TestPriorityLevelModel:
    """Tests for the PriorityLevel model."""

    @pytest.mark.asyncio
    async def test_priority_defaults(self, test_session):
        """Test that default priority levels are seeded."""
        from sqlalchemy import select
        result = await test_session.execute(select(PriorityLevel))
        priorities = list(result.scalars())

        assert len(priorities) == 10
        assert priorities[0].level == 1
        assert priorities[0].name == "Lowest"
        assert priorities[9].level == 10
        assert priorities[9].name == "Urgent"
