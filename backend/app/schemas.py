from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID


# Auth Schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# User Schemas
class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    display_name: str | None = None


# Todo Schemas
class TodoCreate(BaseModel):
    text: str
    completed: bool = False


class TodoUpdate(BaseModel):
    text: str | None = None
    completed: bool | None = None
    version: int  # For conflict resolution


class TodoResponse(BaseModel):
    id: UUID
    user_id: UUID
    text: str
    completed: bool
    created_at: datetime
    updated_at: datetime
    version: int

    class Config:
        from_attributes = True


class TodoSyncRequest(BaseModel):
    todos: list[TodoUpdate]
    last_sync: datetime


class TodoSyncConflict(BaseModel):
    id: UUID
    client_version: int
    server_version: int
    server_data: TodoResponse


class TodoSyncResponse(BaseModel):
    server_changes: list[TodoResponse]
    applied: list[UUID]
    conflicts: list[TodoSyncConflict]
    sync_timestamp: datetime
