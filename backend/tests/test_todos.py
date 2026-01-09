import pytest
from uuid import UUID


def test_create_todo(client, auth_headers):
    """Test creating a todo"""
    response = client.post(
        "/api/v1/todos",
        json={"text": "Test todo", "completed": False},
        headers=auth_headers
    )
    assert response.status_code == 201
    
    data = response.json()
    assert data["text"] == "Test todo"
    assert data["completed"] is False
    assert "id" in data
    assert data["version"] == 1


def test_list_todos(client, auth_headers):
    """Test listing todos"""
    # Create some todos
    for i in range(3):
        client.post(
            "/api/v1/todos",
            json={"text": f"Todo {i}", "completed": False},
            headers=auth_headers
        )
    
    # List todos
    response = client.get("/api/v1/todos", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 3


def test_get_todo(client, auth_headers):
    """Test getting single todo"""
    # Create todo
    create_response = client.post(
        "/api/v1/todos",
        json={"text": "Test todo", "completed": False},
        headers=auth_headers
    )
    todo_id = create_response.json()["id"]
    
    # Get todo
    response = client.get(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == todo_id
    assert data["text"] == "Test todo"


def test_update_todo(client, auth_headers):
    """Test updating a todo"""
    # Create todo
    create_response = client.post(
        "/api/v1/todos",
        json={"text": "Original", "completed": False},
        headers=auth_headers
    )
    todo = create_response.json()
    
    # Update todo
    response = client.patch(
        f"/api/v1/todos/{todo['id']}",
        json={
            "text": "Updated",
            "completed": True,
            "version": todo["version"]
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["text"] == "Updated"
    assert data["completed"] is True
    assert data["version"] == 2


def test_update_conflict(client, auth_headers):
    """Test conflict detection on update"""
    # Create todo
    create_response = client.post(
        "/api/v1/todos",
        json={"text": "Test", "completed": False},
        headers=auth_headers
    )
    todo_id = create_response.json()["id"]
    
    # Try to update with wrong version
    response = client.patch(
        f"/api/v1/todos/{todo_id}",
        json={
            "text": "Updated",
            "completed": False,
            "version": 0  # Wrong version
        },
        headers=auth_headers
    )
    assert response.status_code == 409


def test_delete_todo(client, auth_headers):
    """Test deleting a todo"""
    # Create todo
    create_response = client.post(
        "/api/v1/todos",
        json={"text": "Test", "completed": False},
        headers=auth_headers
    )
    todo_id = create_response.json()["id"]
    
    # Delete todo
    response = client.delete(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert response.status_code == 204
    
    # Verify deleted
    response = client.get(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    assert response.status_code == 404


def test_restore_todo(client, auth_headers):
    """Test restoring a deleted todo"""
    # Create todo
    create_response = client.post(
        "/api/v1/todos",
        json={"text": "Test", "completed": False},
        headers=auth_headers
    )
    todo_id = create_response.json()["id"]
    
    # Delete
    client.delete(f"/api/v1/todos/{todo_id}", headers=auth_headers)
    
    # Restore
    response = client.post(f"/api/v1/todos/{todo_id}/restore", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == todo_id


def test_filter_todos(client, auth_headers):
    """Test filtering todos"""
    # Create completed and incomplete todos
    client.post(
        "/api/v1/todos",
        json={"text": "Active", "completed": False},
        headers=auth_headers
    )
    client.post(
        "/api/v1/todos",
        json={"text": "Done", "completed": True},
        headers=auth_headers
    )
    
    # Filter active
    response = client.get(
        "/api/v1/todos?filter=active",
        headers=auth_headers
    )
    assert len(response.json()) == 1
    
    # Filter completed
    response = client.get(
        "/api/v1/todos?filter=completed",
        headers=auth_headers
    )
    assert len(response.json()) == 1


def test_search_todos(client, auth_headers):
    """Test searching todos"""
    # Create todos
    client.post(
        "/api/v1/todos",
        json={"text": "Buy groceries", "completed": False},
        headers=auth_headers
    )
    client.post(
        "/api/v1/todos",
        json={"text": "Write code", "completed": False},
        headers=auth_headers
    )
    
    # Search
    response = client.get(
        "/api/v1/todos?search=groceries",
        headers=auth_headers
    )
    assert len(response.json()) == 1


def test_unauthenticated_access(client):
    """Test that unauthenticated access is denied"""
    response = client.get("/api/v1/todos")
    assert response.status_code == 403


def test_bulk_create_todos(client, auth_headers):
    """Test bulk creating todos"""
    todos_data = [
        {"text": "Todo 1", "completed": False},
        {"text": "Todo 2", "completed": False},
        {"text": "Todo 3", "completed": True}
    ]
    
    response = client.post(
        "/api/v1/todos/bulk",
        json=todos_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 3
