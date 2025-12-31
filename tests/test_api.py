"""Tests for API endpoints."""

import pytest


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestTodosAPI:
    """Tests for todo CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_todo(self, client):
        """Test creating a new todo."""
        response = await client.post(
            "/api/todos",
            json={"title": "Test todo", "priority": 7}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test todo"
        assert data["priority"] == 7
        assert data["completed"] is False
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_todo_with_defaults(self, client):
        """Test creating a todo with default values."""
        response = await client.post(
            "/api/todos",
            json={"title": "Simple todo"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["priority"] == 5  # Default priority

    @pytest.mark.asyncio
    async def test_list_todos(self, client):
        """Test listing todos."""
        # Create a todo first
        await client.post("/api/todos", json={"title": "Todo 1"})
        await client.post("/api/todos", json={"title": "Todo 2"})

        response = await client.get("/api/todos")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_get_todo(self, client):
        """Test getting a specific todo."""
        # Create a todo
        create_response = await client.post(
            "/api/todos",
            json={"title": "Get me"}
        )
        todo_id = create_response.json()["id"]

        response = await client.get(f"/api/todos/{todo_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Get me"

    @pytest.mark.asyncio
    async def test_get_todo_not_found(self, client):
        """Test getting a non-existent todo."""
        response = await client.get("/api/todos/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_todo(self, client):
        """Test updating a todo."""
        # Create a todo
        create_response = await client.post(
            "/api/todos",
            json={"title": "Original", "priority": 5}
        )
        todo_id = create_response.json()["id"]

        # Update it
        response = await client.put(
            f"/api/todos/{todo_id}",
            json={"title": "Updated", "priority": 8}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated"
        assert data["priority"] == 8

    @pytest.mark.asyncio
    async def test_complete_todo(self, client):
        """Test marking a todo as complete."""
        # Create a todo
        create_response = await client.post(
            "/api/todos",
            json={"title": "Complete me"}
        )
        todo_id = create_response.json()["id"]

        # Complete it
        response = await client.post(f"/api/todos/{todo_id}/complete")
        assert response.status_code == 200
        assert response.json()["completed"] is True
        assert response.json()["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_delete_todo(self, client):
        """Test deleting a todo."""
        # Create a todo
        create_response = await client.post(
            "/api/todos",
            json={"title": "Delete me"}
        )
        todo_id = create_response.json()["id"]

        # Delete it
        response = await client.delete(f"/api/todos/{todo_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(f"/api/todos/{todo_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_subtask(self, client):
        """Test creating a subtask."""
        # Create parent todo
        parent_response = await client.post(
            "/api/todos",
            json={"title": "Parent task"}
        )
        parent_id = parent_response.json()["id"]

        # Create subtask
        response = await client.post(
            f"/api/todos/{parent_id}/subtasks",
            json={"title": "Subtask"}
        )
        assert response.status_code == 201
        assert response.json()["parent_id"] == parent_id

    @pytest.mark.asyncio
    async def test_filter_completed(self, client):
        """Test filtering todos by completion status."""
        # Create todos
        resp1 = await client.post("/api/todos", json={"title": "Incomplete"})
        resp2 = await client.post("/api/todos", json={"title": "Complete"})
        await client.post(f"/api/todos/{resp2.json()['id']}/complete")

        # Filter incomplete
        response = await client.get("/api/todos?completed=false")
        data = response.json()
        assert all(not item["completed"] for item in data["items"])

        # Filter completed
        response = await client.get("/api/todos?completed=true")
        data = response.json()
        assert all(item["completed"] for item in data["items"])


class TestCategoriesAPI:
    """Tests for category endpoints."""

    @pytest.mark.asyncio
    async def test_create_category(self, client):
        """Test creating a category."""
        response = await client.post(
            "/api/categories",
            json={"name": "Work", "color": "#0000FF"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Work"
        assert data["color"] == "#0000FF"

    @pytest.mark.asyncio
    async def test_list_categories(self, client):
        """Test listing categories."""
        await client.post("/api/categories", json={"name": "Cat1"})
        await client.post("/api/categories", json={"name": "Cat2"})

        response = await client.get("/api/categories")
        assert response.status_code == 200
        assert len(response.json()) >= 2

    @pytest.mark.asyncio
    async def test_delete_category(self, client):
        """Test deleting a category."""
        create_response = await client.post(
            "/api/categories",
            json={"name": "ToDelete"}
        )
        cat_id = create_response.json()["id"]

        response = await client.delete(f"/api/categories/{cat_id}")
        assert response.status_code == 204


class TestTagsAPI:
    """Tests for tag endpoints."""

    @pytest.mark.asyncio
    async def test_create_tag(self, client):
        """Test creating a tag."""
        response = await client.post(
            "/api/tags",
            json={"name": "urgent", "color": "#FF0000"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "urgent"

    @pytest.mark.asyncio
    async def test_list_tags(self, client):
        """Test listing tags."""
        await client.post("/api/tags", json={"name": "tag1"})
        await client.post("/api/tags", json={"name": "tag2"})

        response = await client.get("/api/tags")
        assert response.status_code == 200
        assert len(response.json()) >= 2


class TestPrioritiesAPI:
    """Tests for priority level endpoints."""

    @pytest.mark.asyncio
    async def test_list_priorities(self, client):
        """Test listing priority levels."""
        response = await client.get("/api/priorities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        assert data[0]["level"] == 1
        assert data[9]["level"] == 10

    @pytest.mark.asyncio
    async def test_update_priority(self, client):
        """Test updating a priority level name."""
        response = await client.put(
            "/api/priorities/5",
            json={"name": "Medium", "color": "#FFFF00"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Medium"
        assert data["color"] == "#FFFF00"
