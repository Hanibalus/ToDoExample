from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from uuid import UUID

from app.database import get_db_session
from app.models import User, Todo
from app.schemas import (
    TodoCreate, TodoUpdate, TodoResponse,
    TodoSyncRequest, TodoSyncResponse, TodoSyncConflict
)
from app.deps import get_current_user

router = APIRouter()


@router.get("/todos", response_model=list[TodoResponse])
async def list_todos(
    filter: str = "all",
    search: str | None = None,
    sort: str = "newest",
    page: int = 1,
    per_page: int = 50,
    since: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List user's todos with filtering, searching, and sorting"""
    query = select(Todo).where(
        Todo.user_id == current_user.id,
        Todo.deleted_at.is_(None)
    )
    
    # Apply search filter
    if search:
        query = query.where(Todo.text.ilike(f"%{search}%"))
    
    # Apply status filter
    if filter == "active":
        query = query.where(Todo.completed == False)
    elif filter == "completed":
        query = query.where(Todo.completed == True)
    
    # Apply incremental sync filter
    if since:
        query = query.where(Todo.updated_at >= since)
    
    # Apply sorting
    if sort == "oldest":
        query = query.order_by(Todo.created_at)
    elif sort == "alpha":
        query = query.order_by(Todo.text)
    else:  # newest (default)
        query = query.order_by(Todo.created_at.desc())
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/todos", response_model=TodoResponse, status_code=201)
async def create_todo(
    todo_data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new todo"""
    new_todo = Todo(
        user_id=current_user.id,
        text=todo_data.text,
        completed=todo_data.completed
    )
    db.add(new_todo)
    await db.commit()
    await db.refresh(new_todo)
    return new_todo


@router.get("/todos/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get a single todo"""
    result = await db.execute(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == current_user.id,
            Todo.deleted_at.is_(None)
        )
    )
    todo = result.scalar_one_or_none()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    return todo


@router.patch("/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: UUID,
    todo_update: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update a todo with conflict resolution"""
    result = await db.execute(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == current_user.id,
            Todo.deleted_at.is_(None)
        )
    )
    todo = result.scalar_one_or_none()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    # Check version for conflict resolution
    if todo.version != todo_update.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Version mismatch - conflict detected",
            headers={"X-Conflict": "true"}
        )
    
    # Apply updates
    if todo_update.text is not None:
        todo.text = todo_update.text
    if todo_update.completed is not None:
        todo.completed = todo_update.completed
    
    # Increment version
    todo.version += 1
    todo.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(todo)
    return todo


@router.delete("/todos/{todo_id}", status_code=204)
async def delete_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a todo"""
    result = await db.execute(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == current_user.id,
            Todo.deleted_at.is_(None)
        )
    )
    todo = result.scalar_one_or_none()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    # Soft delete
    todo.deleted_at = datetime.utcnow()
    await db.commit()


@router.post("/todos/{todo_id}/restore", response_model=TodoResponse)
async def restore_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Restore a deleted todo"""
    result = await db.execute(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == current_user.id,
            Todo.deleted_at.isnot(None)
        )
    )
    todo = result.scalar_one_or_none()
    
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deleted todo not found"
        )
    
    todo.deleted_at = None
    await db.commit()
    await db.refresh(todo)
    return todo


@router.post("/todos/bulk", response_model=list[TodoResponse])
async def bulk_create_todos(
    todos_data: list[TodoCreate],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create multiple todos (used for localStorage migration)"""
    new_todos = [
        Todo(
            user_id=current_user.id,
            text=todo.text,
            completed=todo.completed
        )
        for todo in todos_data
    ]
    
    db.add_all(new_todos)
    await db.commit()
    
    for todo in new_todos:
        await db.refresh(todo)
    
    return new_todos


@router.post("/todos/sync", response_model=TodoSyncResponse)
async def sync_todos(
    sync_request: TodoSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Sync todos with conflict resolution"""
    applied = []
    conflicts = []
    
    for client_todo in sync_request.todos:
        # Fetch server todo
        result = await db.execute(
            select(Todo).where(
                Todo.id == client_todo.id,
                Todo.user_id == current_user.id
            )
        )
        server_todo = result.scalar_one_or_none()
        
        if not server_todo:
            # Todo doesn't exist - create it
            new_todo = Todo(
                user_id=current_user.id,
                text=client_todo.text,
                completed=client_todo.completed
            )
            db.add(new_todo)
            applied.append(client_todo.id)
        elif server_todo.version != client_todo.version:
            # Conflict - version mismatch
            conflicts.append(TodoSyncConflict(
                id=server_todo.id,
                client_version=client_todo.version,
                server_version=server_todo.version,
                server_data=TodoResponse.from_orm(server_todo)
            ))
        else:
            # No conflict - apply update
            if client_todo.text is not None:
                server_todo.text = client_todo.text
            if client_todo.completed is not None:
                server_todo.completed = client_todo.completed
            server_todo.version += 1
            server_todo.updated_at = datetime.utcnow()
            applied.append(client_todo.id)
    
    await db.commit()
    
    # Get server changes since last sync
    result = await db.execute(
        select(Todo).where(
            Todo.user_id == current_user.id,
            Todo.deleted_at.is_(None),
            Todo.updated_at >= sync_request.last_sync
        )
    )
    server_changes = result.scalars().all()
    
    return TodoSyncResponse(
        server_changes=server_changes,
        applied=applied,
        conflicts=conflicts,
        sync_timestamp=datetime.utcnow()
    )
