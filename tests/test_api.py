"""Tests for API endpoints."""

import io
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
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 2

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
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 2


class TestPrioritiesAPI:
    """Tests for priority level endpoints."""

    @pytest.mark.asyncio
    async def test_list_priorities(self, client):
        """Test listing priority levels."""
        response = await client.get("/api/priorities")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 10
        assert len(data["items"]) == 10
        assert data["items"][0]["level"] == 1
        assert data["items"][9]["level"] == 10

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


class TestAttachmentsAPI:
    """Tests for attachment endpoints."""

    @pytest.mark.asyncio
    async def test_upload_attachment(self, client, test_attachments_dir):
        """Test uploading a file attachment."""
        # Create a todo first
        todo_response = await client.post(
            "/api/todos",
            json={"title": "Todo with attachment"}
        )
        todo_id = todo_response.json()["id"]

        # Create a test PDF file (with valid magic bytes)
        pdf_content = b"%PDF-1.4 test content"

        response = await client.post(
            f"/api/todos/{todo_id}/attachments",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["original_name"] == "test.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["size_bytes"] == len(pdf_content)
        assert "id" in data

    @pytest.mark.asyncio
    async def test_upload_attachment_to_nonexistent_todo(self, client, test_attachments_dir):
        """Test uploading to a non-existent todo returns 404."""
        pdf_content = b"%PDF-1.4 test content"

        response = await client.post(
            "/api/todos/nonexistent-id/attachments",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_disallowed_file_type(self, client, test_attachments_dir):
        """Test that disallowed file types are rejected."""
        # Create a todo first
        todo_response = await client.post(
            "/api/todos",
            json={"title": "Todo for bad file"}
        )
        todo_id = todo_response.json()["id"]

        # Try to upload an executable
        exe_content = b"MZ\x90\x00"  # PE executable magic bytes

        response = await client.post(
            f"/api/todos/{todo_id}/attachments",
            files={"file": ("malware.exe", io.BytesIO(exe_content), "application/octet-stream")}
        )

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_mismatched_content(self, client, test_attachments_dir):
        """Test that files with mismatched content/extension are rejected."""
        # Create a todo first
        todo_response = await client.post(
            "/api/todos",
            json={"title": "Todo for mismatched file"}
        )
        todo_id = todo_response.json()["id"]

        # Send a text file claiming to be a PNG
        text_content = b"This is just text, not an image"

        response = await client.post(
            f"/api/todos/{todo_id}/attachments",
            files={"file": ("fake.png", io.BytesIO(text_content), "image/png")}
        )

        assert response.status_code == 400
        assert "does not match" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_download_attachment(self, client, test_attachments_dir):
        """Test downloading an attachment."""
        # Create a todo and upload a file
        todo_response = await client.post(
            "/api/todos",
            json={"title": "Todo for download"}
        )
        todo_id = todo_response.json()["id"]

        pdf_content = b"%PDF-1.4 test content for download"

        # Upload
        upload_response = await client.post(
            f"/api/todos/{todo_id}/attachments",
            files={"file": ("download.pdf", io.BytesIO(pdf_content), "application/pdf")}
        )
        attachment_id = upload_response.json()["id"]

        # Download
        response = await client.get(f"/api/attachments/{attachment_id}")

        assert response.status_code == 200
        assert response.content == pdf_content
        assert "attachment" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_delete_attachment(self, client, test_attachments_dir):
        """Test deleting an attachment."""
        # Create a todo and upload a file
        todo_response = await client.post(
            "/api/todos",
            json={"title": "Todo for delete"}
        )
        todo_id = todo_response.json()["id"]

        pdf_content = b"%PDF-1.4 test content to delete"

        # Upload
        upload_response = await client.post(
            f"/api/todos/{todo_id}/attachments",
            files={"file": ("todelete.pdf", io.BytesIO(pdf_content), "application/pdf")}
        )
        attachment_id = upload_response.json()["id"]

        # Delete
        response = await client.delete(f"/api/attachments/{attachment_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(f"/api/attachments/{attachment_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_download_nonexistent_attachment(self, client):
        """Test downloading a non-existent attachment returns 404."""
        response = await client.get("/api/attachments/nonexistent-id")
        assert response.status_code == 404


class TestEdgeCases:
    """Tests for edge cases and validation."""

    @pytest.mark.asyncio
    async def test_create_todo_empty_title(self, client):
        """Test that empty title is rejected."""
        response = await client.post(
            "/api/todos",
            json={"title": ""}
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_todo_priority_out_of_range(self, client):
        """Test that priority outside 1-10 is rejected."""
        response = await client.post(
            "/api/todos",
            json={"title": "Test", "priority": 11}
        )
        assert response.status_code == 422

        response = await client.post(
            "/api/todos",
            json={"title": "Test", "priority": 0}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_category_invalid_color(self, client):
        """Test that invalid color format is rejected."""
        response = await client.post(
            "/api/categories",
            json={"name": "Test", "color": "not-a-color"}
        )
        assert response.status_code == 422

        response = await client.post(
            "/api/categories",
            json={"name": "Test", "color": "#GGG"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_priority_invalid_level(self, client):
        """Test that invalid priority level is rejected."""
        response = await client.put(
            "/api/priorities/0",
            json={"name": "Invalid"}
        )
        assert response.status_code == 400

        response = await client.put(
            "/api/priorities/11",
            json={"name": "Invalid"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_patch_todo(self, client):
        """Test PATCH endpoint for partial updates."""
        # Create a todo
        create_response = await client.post(
            "/api/todos",
            json={"title": "Original", "priority": 5, "description": "Original desc"}
        )
        todo_id = create_response.json()["id"]

        # Patch only the title
        response = await client.patch(
            f"/api/todos/{todo_id}",
            json={"title": "Patched"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Patched"
        assert data["priority"] == 5  # Unchanged
        assert data["description"] == "Original desc"  # Unchanged

    @pytest.mark.asyncio
    async def test_patch_category(self, client):
        """Test PATCH endpoint for categories."""
        # Create a category
        create_response = await client.post(
            "/api/categories",
            json={"name": "Original", "color": "#FF0000"}
        )
        cat_id = create_response.json()["id"]

        # Patch only the color
        response = await client.patch(
            f"/api/categories/{cat_id}",
            json={"color": "#00FF00"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Original"  # Unchanged
        assert data["color"] == "#00FF00"

    @pytest.mark.asyncio
    async def test_pagination(self, client):
        """Test pagination parameters."""
        # Create multiple todos
        for i in range(15):
            await client.post("/api/todos", json={"title": f"Todo {i}"})

        # Get first page
        response = await client.get("/api/todos?page=1&page_size=5")
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert data["total"] >= 15

        # Get second page
        response = await client.get("/api/todos?page=2&page_size=5")
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 2

    @pytest.mark.asyncio
    async def test_filter_by_priority_range(self, client):
        """Test filtering todos by priority range."""
        # Create todos with different priorities
        await client.post("/api/todos", json={"title": "Low", "priority": 2})
        await client.post("/api/todos", json={"title": "Medium", "priority": 5})
        await client.post("/api/todos", json={"title": "High", "priority": 8})

        # Filter by priority range
        response = await client.get("/api/todos?priority_min=4&priority_max=6")
        data = response.json()
        for item in data["items"]:
            assert 4 <= item["priority"] <= 6

    @pytest.mark.asyncio
    async def test_subtask_depth_limit_api(self, client):
        """Test that subtask depth limit is enforced via API."""
        # Create a chain of subtasks up to limit
        parent_response = await client.post("/api/todos", json={"title": "Level 0"})
        parent_id = parent_response.json()["id"]

        # Create 5 levels of subtasks (max depth is 5)
        current_id = parent_id
        for i in range(1, 6):
            response = await client.post(
                f"/api/todos/{current_id}/subtasks",
                json={"title": f"Level {i}"}
            )
            assert response.status_code == 201
            current_id = response.json()["id"]

        # 6th level should fail
        response = await client.post(
            f"/api/todos/{current_id}/subtasks",
            json={"title": "Level 6 - Too Deep"}
        )
        assert response.status_code == 400
        assert "depth" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_circular_reference_api(self, client):
        """Test that circular references are prevented via API."""
        # Create A -> B chain
        a_response = await client.post("/api/todos", json={"title": "A"})
        a_id = a_response.json()["id"]

        b_response = await client.post(
            f"/api/todos/{a_id}/subtasks",
            json={"title": "B"}
        )
        b_id = b_response.json()["id"]

        # Try to make A a child of B (would create B -> A -> B cycle)
        response = await client.patch(
            f"/api/todos/{a_id}",
            json={"parent_id": b_id}
        )
        assert response.status_code == 400
        assert "circular" in response.json()["detail"].lower()
