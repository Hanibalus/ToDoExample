# FastAPI Backend Design - Production-Grade Multi-User Todo Sync

**Design Date:** January 9, 2026  
**Status:** Design Complete - Ready for Implementation  
**Type:** New Feature - Backend API  

---

## Executive Summary

This design adds a FastAPI backend to the existing vanilla JavaScript todo app, enabling multi-user synchronization across devices. The architecture prioritizes progressive enhancement: anonymous users continue working offline with localStorage, while authenticated users gain cloud sync with real-time updates via WebSockets.

**Key Features:**
- Multi-provider authentication (email/password, Google OAuth, GitHub OAuth, magic links)
- Real-time sync across devices via WebSockets
- Conflict resolution with optimistic locking
- Seamless migration from localStorage to cloud storage
- Production-ready security and scalability

---

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Framework** | FastAPI | Async/await, automatic OpenAPI docs, modern Python |
| **Database** | SQLAlchemy 2.0 + Alembic | ORM flexibility (SQLite dev → PostgreSQL prod) |
| **Validation** | Pydantic v2 | Type-safe request/response validation |
| **Authentication** | JWT + OAuth 2.0 | Industry standard, stateless, secure |
| **Real-time** | WebSockets | Bi-directional sync, low latency |
| **Caching** | Redis | Rate limiting, session storage, query cache |
| **Testing** | Pytest + httpx | Async test support, comprehensive coverage |
| **Deployment** | Docker Compose | Reproducible environments, easy scaling |

---

## Database Schema

### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),  -- nullable for OAuth users
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP,
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_email ON users(email);
```

### oauth_accounts
```sql
CREATE TABLE oauth_accounts (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL,  -- 'google', 'github'
    provider_user_id VARCHAR(255) NOT NULL,
    access_token TEXT,  -- encrypted
    refresh_token TEXT,  -- encrypted
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(provider, provider_user_id)
);

CREATE INDEX idx_oauth_user_id ON oauth_accounts(user_id);
```

### todos
```sql
CREATE TABLE todos (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    text VARCHAR(500) NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP,  -- soft delete for undo
    client_id VARCHAR(100),  -- device identifier
    version INTEGER NOT NULL DEFAULT 1  -- optimistic locking
);

CREATE INDEX idx_todos_user_id ON todos(user_id);
CREATE INDEX idx_todos_updated_at ON todos(updated_at);
CREATE INDEX idx_todos_deleted_at ON todos(deleted_at);
```

### refresh_tokens
```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
```

**Design Decisions:**
- **UUIDs**: Support distributed systems, prevent enumeration attacks
- **Soft deletes**: Enable undo functionality, maintain sync history
- **Version field**: Optimistic locking prevents concurrent edit conflicts
- **Client_id**: Track which device made changes for debugging
- **Encrypted tokens**: PCI/SOC2 compliance for OAuth credentials

---

## API Endpoints

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Create account with email/password | No |
| POST | `/auth/login` | Login with email/password | No |
| POST | `/auth/refresh` | Refresh access token | Refresh token |
| POST | `/auth/logout` | Revoke refresh token | Yes |
| POST | `/auth/verify-email` | Verify email with token | No |
| POST | `/auth/forgot-password` | Request password reset email | No |
| POST | `/auth/reset-password` | Reset password with token | No |
| GET | `/auth/oauth/{provider}/login` | Redirect to OAuth provider | No |
| GET | `/auth/oauth/{provider}/callback` | Handle OAuth callback | No |
| POST | `/auth/oauth/{provider}/link` | Link OAuth to existing account | Yes |
| POST | `/auth/magic-link/request` | Send magic link email | No |
| GET | `/auth/magic-link/verify` | Verify and login with magic link | No |

**Request/Response Examples:**

```json
// POST /auth/register
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "display_name": "John Doe"
}

// Response
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "dGhpcyBpc...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "display_name": "John Doe",
    "email_verified": false
  }
}
```

### Todo Management (`/api/v1/todos`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/todos` | List all todos with filters/pagination | Yes |
| POST | `/todos` | Create new todo | Yes |
| GET | `/todos/{id}` | Get single todo | Yes |
| PATCH | `/todos/{id}` | Update todo (partial) | Yes |
| DELETE | `/todos/{id}` | Soft delete todo | Yes |
| POST | `/todos/{id}/restore` | Restore deleted todo | Yes |
| POST | `/todos/bulk` | Create multiple todos | Yes |
| PATCH | `/todos/bulk` | Bulk update | Yes |
| POST | `/todos/sync` | Sync with conflict resolution | Yes |

**Query Parameters (GET /todos):**
- `filter`: `all` | `active` | `completed`
- `search`: Text search in todo content
- `sort`: `newest` | `oldest` | `alpha`
- `page`: Page number (default: 1)
- `per_page`: Results per page (default: 50, max: 100)
- `since`: ISO timestamp for incremental sync
- `include_deleted`: Include soft-deleted todos (default: false)

**Sync Endpoint Example:**

```json
// POST /todos/sync
{
  "todos": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "text": "Updated todo",
      "completed": true,
      "version": 2,
      "updated_at": "2026-01-09T10:30:00Z"
    }
  ],
  "last_sync": "2026-01-09T10:00:00Z"
}

// Response
{
  "server_changes": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "text": "New from another device",
      "completed": false,
      "version": 1,
      "created_at": "2026-01-09T10:15:00Z"
    }
  ],
  "applied": ["550e8400-e29b-41d4-a716-446655440000"],
  "conflicts": [],
  "sync_timestamp": "2026-01-09T10:35:00Z"
}
```

### User Management (`/api/v1/users`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/users/me` | Get current user profile | Yes |
| PATCH | `/users/me` | Update profile | Yes |
| DELETE | `/users/me` | Delete account (GDPR) | Yes |
| GET | `/users/me/devices` | List active sessions | Yes |
| DELETE | `/users/me/devices/{id}` | Revoke device session | Yes |

### WebSocket (`/ws`)

```
WS /ws/todos?token={access_token}
```

**Message Types:**
```json
// Server → Client
{
  "type": "todo_created",
  "todo": { /* todo object */ }
}

{
  "type": "todo_updated",
  "todo": { /* todo object */ }
}

{
  "type": "todo_deleted",
  "todo_id": "uuid"
}

{
  "type": "todo_restored",
  "todo": { /* todo object */ }
}

// Client → Server (heartbeat)
{
  "type": "ping"
}

// Server → Client (response)
{
  "type": "pong"
}
```

---

## Security Architecture

### Authentication Flow

**JWT Token Strategy:**
- **Access token**: Short-lived (15 minutes), contains user_id and permissions
- **Refresh token**: Long-lived (7 days), stored as hash in database
- **Token rotation**: New refresh token issued on each refresh
- **Revocation**: Logout invalidates refresh token immediately

```python
# Token Structure
access_token = {
    "sub": "user_id",
    "exp": datetime.utcnow() + timedelta(minutes=15),
    "type": "access"
}

refresh_token = secrets.token_urlsafe(32)  # Cryptographically secure
```

### OAuth Flow

```mermaid
sequenceDiagram
    User->>Frontend: Click "Login with Google"
    Frontend->>Backend: GET /auth/oauth/google/login
    Backend->>User: Redirect to Google
    User->>Google: Authorize app
    Google->>Backend: Callback with auth code
    Backend->>Google: Exchange code for tokens
    Google->>Backend: Return access token
    Backend->>Backend: Create/update user
    Backend->>Frontend: Redirect with JWT tokens
    Frontend->>Backend: Use JWT for API calls
```

### Password Security
- **Hashing**: bcrypt with 12 rounds
- **Validation**: Minimum 8 characters, mix of upper/lower/number
- **Reset tokens**: Time-limited (1 hour), single-use
- **Rate limiting**: 5 login attempts per 15 minutes per IP

### CORS Configuration
```python
ALLOWED_ORIGINS = [
    "http://localhost:5000",
    "https://yourdomain.com"
]
allow_credentials = True  # For cookies/auth headers
```

---

## Sync and Conflict Resolution

### Conflict Resolution Strategy

**Problem:** Two devices edit the same todo offline, then both sync.

**Solution:** Optimistic locking with version numbers

```python
class ConflictResolution:
    """
    1. Client sends update with version number
    2. Server checks if version matches current
    3. If match: Apply update, increment version
    4. If mismatch: Return conflict with server state
    5. Client must merge and retry
    """
    
    def resolve_conflict(client_todo, server_todo):
        if client_todo.version == server_todo.version:
            # No conflict - apply update
            return apply_update(client_todo)
        else:
            # Conflict - return both versions
            return {
                "conflict": True,
                "client_version": client_todo.version,
                "server_version": server_todo.version,
                "server_data": server_todo,
                "resolution_strategy": "last_write_wins"
            }
```

**Client Conflict Handling:**
```javascript
async function handleConflict(conflict) {
    // Simple strategy: Server wins, notify user
    const serverTodo = conflict.server_data;
    
    // Update local state
    updateLocalTodo(serverTodo);
    
    // Show notification
    showNotification(`Todo "${serverTodo.text}" was updated on another device`);
}
```

### Incremental Sync

**On app load:**
1. Send `last_sync` timestamp to server
2. Receive only todos modified since that time
3. Merge with local state
4. Update `last_sync` timestamp

**Benefits:**
- Reduces bandwidth
- Faster sync times
- Better mobile experience

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app initialization
│   ├── config.py                  # Settings (Pydantic BaseSettings)
│   ├── database.py                # SQLAlchemy engine and session
│   ├── deps.py                    # Shared dependencies
│   │
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── todo.py
│   │   ├── oauth_account.py
│   │   └── refresh_token.py
│   │
│   ├── schemas/                   # Pydantic validation schemas
│   │   ├── __init__.py
│   │   ├── user.py                # UserCreate, UserUpdate, UserResponse
│   │   ├── todo.py                # TodoCreate, TodoUpdate, TodoResponse
│   │   ├── auth.py                # LoginRequest, RegisterRequest
│   │   └── token.py               # TokenResponse, RefreshRequest
│   │
│   ├── api/                       # API route handlers
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py            # Authentication routes
│   │   │   ├── todos.py           # Todo CRUD + sync
│   │   │   └── users.py           # User profile management
│   │   └── deps.py                # Route-level dependencies
│   │
│   ├── core/                      # Core utilities
│   │   ├── __init__.py
│   │   ├── security.py            # JWT, password hashing, encryption
│   │   ├── oauth.py               # OAuth provider configuration
│   │   └── websocket.py           # WebSocket connection manager
│   │
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py        # Authentication logic
│   │   ├── todo_service.py        # Todo business logic
│   │   ├── sync_service.py        # Conflict resolution
│   │   └── email_service.py       # Email sending (verification, magic links)
│   │
│   └── middleware/                # Custom middleware
│       ├── __init__.py
│       ├── rate_limit.py          # Rate limiting with Redis
│       └── cors.py                # CORS configuration
│
├── alembic/                       # Database migrations
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_oauth.py
│   │   └── 003_add_soft_delete.py
│   ├── env.py
│   └── script.py.mako
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── test_auth.py               # Auth endpoint tests
│   ├── test_todos.py              # Todo CRUD tests
│   ├── test_sync.py               # Conflict resolution tests
│   ├── test_websocket.py          # WebSocket tests
│   └── test_oauth.py              # OAuth flow tests
│
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   └── docker-compose.yml
│
├── .env.example
├── .gitignore
├── alembic.ini
├── pytest.ini
├── pyproject.toml                 # Poetry dependencies
└── README.md
```

---

## Dependencies

### Production Dependencies
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109.0"              # Web framework
uvicorn = {extras = ["standard"], version = "^0.27.0"}  # ASGI server
sqlalchemy = "^2.0.25"            # ORM
alembic = "^1.13.1"               # Database migrations
asyncpg = "^0.29.0"               # PostgreSQL async driver
aiosqlite = "^0.19.0"             # SQLite async driver
pydantic = {extras = ["email"], version = "^2.5.3"}  # Validation
pydantic-settings = "^2.1.0"     # Settings management
python-jose = {extras = ["cryptography"], version = "^3.3.0"}  # JWT
passlib = {extras = ["bcrypt"], version = "^1.7.4"}  # Password hashing
python-multipart = "^0.0.6"      # Form data parsing
authlib = "^1.3.0"                # OAuth client
httpx = "^0.26.0"                 # HTTP client
redis = "^5.0.1"                  # Caching and rate limiting
python-dotenv = "^1.0.0"          # Environment variables
emails = "^0.6"                   # Email sending
```

### Development Dependencies
```toml
[tool.poetry.group.dev.dependencies]
pytest = "^7.4.4"
pytest-asyncio = "^0.23.3"
pytest-cov = "^4.1.0"
httpx = "^0.26.0"
faker = "^22.0.0"                 # Test data generation
black = "^23.12.1"                # Code formatting
ruff = "^0.1.11"                  # Linting
```

---

## Frontend Integration

### New Files

**`frontend/api/client.js`** - API client wrapper
```javascript
class TodoAPI {
  constructor() {
    this.baseURL = 'http://localhost:8000/api/v1';
    this.accessToken = localStorage.getItem('access_token');
    this.ws = null;
  }

  async register(email, password, displayName) {
    const response = await fetch(`${this.baseURL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, display_name: displayName })
    });
    const data = await response.json();
    this.setTokens(data.access_token, data.refresh_token);
    await this.migrateLocalTodos();
    return data;
  }

  async migrateLocalTodos() {
    const localTodos = JSON.parse(localStorage.getItem('simple_todos_v1') || '[]');
    if (localTodos.length > 0) {
      await fetch(`${this.baseURL}/todos/bulk`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ todos: localTodos })
      });
      localStorage.removeItem('simple_todos_v1');
    }
  }

  connectWebSocket(onMessage) {
    this.ws = new WebSocket(`ws://localhost:8000/ws/todos?token=${this.accessToken}`);
    this.ws.onmessage = (event) => onMessage(JSON.parse(event.data));
  }

  getHeaders() {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.accessToken}`
    };
  }

  setTokens(accessToken, refreshToken) {
    this.accessToken = accessToken;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }
}
```

### Modified Files

**`index.html`** - Add auth UI
```html
<!-- Add after app-header -->
<div id="auth-section" class="auth-section">
  <button id="login-btn">Login</button>
  <button id="signup-btn">Sign Up</button>
  <div id="user-info" style="display:none">
    <span id="user-email"></span>
    <button id="logout-btn">Logout</button>
  </div>
</div>

<!-- Add login modal -->
<div id="login-modal" class="modal" style="display:none">
  <div class="modal-content">
    <h2>Login</h2>
    <form id="login-form">
      <input type="email" name="email" placeholder="Email" required>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">Login</button>
    </form>
    <button id="google-login">Login with Google</button>
    <button id="github-login">Login with GitHub</button>
  </div>
</div>
```

**`app.js`** - Add auth logic
```javascript
const api = new TodoAPI();

async function loadTodos() {
  if (api.accessToken) {
    // Authenticated - load from server
    const response = await fetch('http://localhost:8000/api/v1/todos', {
      headers: api.getHeaders()
    });
    todos = await response.json();
    api.connectWebSocket(handleWebSocketMessage);
  } else {
    // Anonymous - use localStorage
    todos = JSON.parse(localStorage.getItem('simple_todos_v1') || '[]');
  }
  render();
}

function handleWebSocketMessage(message) {
  switch (message.type) {
    case 'todo_created':
      todos.push(message.todo);
      render();
      break;
    case 'todo_updated':
      const index = todos.findIndex(t => t.id === message.todo.id);
      if (index !== -1) {
        todos[index] = message.todo;
        render();
      }
      break;
    case 'todo_deleted':
      todos = todos.filter(t => t.id !== message.todo_id);
      render();
      break;
  }
}
```

---

## Testing Strategy

### Test Coverage Goals
- **Unit tests**: 80%+ coverage
- **Integration tests**: All API endpoints
- **End-to-end**: Critical user flows

### Test Categories

**1. Unit Tests** (Fast, isolated)
```python
def test_password_hashing():
    password = "SecurePass123!"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("WrongPass", hashed)

def test_jwt_creation():
    token = create_access_token("user-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
```

**2. API Tests** (Integration)
```python
def test_create_todo_authenticated(client, auth_headers):
    response = client.post("/api/v1/todos", 
        json={"text": "Test todo", "completed": False},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["text"] == "Test todo"
    assert "id" in data

def test_create_todo_unauthenticated(client):
    response = client.post("/api/v1/todos",
        json={"text": "Test"}
    )
    assert response.status_code == 401
```

**3. Sync Tests** (Complex scenarios)
```python
def test_conflict_resolution(client, auth_headers):
    # Create todo
    todo = client.post("/api/v1/todos", 
        json={"text": "Original"}, 
        headers=auth_headers
    ).json()
    
    # Simulate conflict - stale version
    response = client.patch(f"/api/v1/todos/{todo['id']}",
        json={"text": "Updated", "version": 0},
        headers=auth_headers
    )
    
    assert response.status_code == 409
    assert "conflict" in response.json()["detail"].lower()
```

**4. WebSocket Tests**
```python
async def test_websocket_broadcast(client, auth_headers):
    with client.websocket_connect(f"/ws/todos?token={token}") as ws1, \
         client.websocket_connect(f"/ws/todos?token={token}") as ws2:
        
        # Create todo via API
        client.post("/api/v1/todos", json={"text": "Test"})
        
        # Both WebSockets should receive update
        msg1 = ws1.receive_json()
        msg2 = ws2.receive_json()
        
        assert msg1["type"] == "todo_created"
        assert msg2["type"] == "todo_created"
```

---

## Configuration

### Environment Variables (`.env`)

```bash
# Application
APP_NAME="Todo API"
DEBUG=False
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32

# Database
DATABASE_URL=sqlite:///./todos.db
# Production: postgresql+asyncpg://user:pass@host:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379

# CORS
ALLOWED_ORIGINS=["http://localhost:5000","https://yourdomain.com"]

# OAuth - Google
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# OAuth - GitHub
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM=noreply@todoapp.com

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## Deployment

### Docker Compose (Development)

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/todos
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./app:/app/app
    depends_on:
      - db
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=todos
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Production Checklist

**Pre-Deployment:**
- [ ] Change `SECRET_KEY` to strong random value
- [ ] Set `DEBUG=False`
- [ ] Configure production `DATABASE_URL` (PostgreSQL)
- [ ] Set up Redis instance
- [ ] Configure OAuth credentials for production domain
- [ ] Set up SMTP for email sending
- [ ] Add SSL certificate
- [ ] Configure firewall rules

**Security:**
- [ ] Enable rate limiting
- [ ] Set restrictive CORS origins
- [ ] Use HTTPS only
- [ ] Rotate secrets regularly
- [ ] Enable database connection pooling
- [ ] Set up automated backups

**Monitoring:**
- [ ] Add logging (JSON structured logs)
- [ ] Set up error tracking (Sentry)
- [ ] Monitor endpoint performance
- [ ] Track WebSocket connections
- [ ] Set up health check monitoring
- [ ] Database query performance monitoring

**Performance:**
- [ ] Enable Redis caching
- [ ] Add CDN for static assets
- [ ] Enable Gzip compression
- [ ] Optimize database indexes
- [ ] Set up connection pooling

---

## Implementation Phases

### Phase 1: Core Backend (Week 1)
**Goal:** Basic FastAPI app with email/password auth and CRUD

- [ ] Set up project structure
- [ ] Configure SQLAlchemy with SQLite
- [ ] Create database models (User, Todo, RefreshToken)
- [ ] Implement password hashing and JWT
- [ ] Build `/auth/register` and `/auth/login` endpoints
- [ ] Create basic CRUD endpoints for todos
- [ ] Write unit tests for security functions
- [ ] Write API tests for auth and todos

**Deliverable:** Working API with email/password auth and todo management

### Phase 2: Sync Logic (Week 2)
**Goal:** Conflict resolution and WebSocket support

- [ ] Implement version-based conflict resolution
- [ ] Build `/todos/sync` endpoint
- [ ] Add incremental sync with `since` parameter
- [ ] Implement WebSocket connection manager
- [ ] Build WebSocket broadcast for real-time updates
- [ ] Add soft delete support
- [ ] Write sync conflict tests
- [ ] Write WebSocket integration tests

**Deliverable:** Multi-device sync with conflict handling

### Phase 3: OAuth & Advanced Auth (Week 3)
**Goal:** Multiple authentication methods

- [ ] Integrate Authlib for OAuth
- [ ] Implement Google OAuth flow
- [ ] Implement GitHub OAuth flow
- [ ] Add OAuth account linking
- [ ] Build magic link authentication
- [ ] Implement email verification
- [ ] Add password reset functionality
- [ ] Write OAuth flow tests

**Deliverable:** Complete authentication system

### Phase 4: Frontend Integration (Week 4)
**Goal:** Connect frontend to backend

- [ ] Create API client wrapper (`api/client.js`)
- [ ] Build login/register UI
- [ ] Implement localStorage → server migration
- [ ] Add WebSocket integration to frontend
- [ ] Handle authentication state
- [ ] Implement token refresh logic
- [ ] Add error handling and retry logic
- [ ] Update offline fallback behavior

**Deliverable:** Fully integrated frontend with backend sync

### Phase 5: Production Ready (Week 5)
**Goal:** Deploy to production

- [ ] Add rate limiting with Redis
- [ ] Implement email service
- [ ] Set up logging and monitoring
- [ ] Write deployment documentation
- [ ] Create Docker production images
- [ ] Set up CI/CD pipeline
- [ ] Perform load testing
- [ ] Security audit

**Deliverable:** Production deployment

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Conflict resolution too complex** | High | Start with simple last-write-wins, iterate based on usage |
| **OAuth provider downtime** | Medium | Always support email/password as fallback |
| **WebSocket connection limits** | Medium | Use Redis pub/sub for horizontal scaling |
| **Database migration issues** | High | Test migrations thoroughly, maintain rollback scripts |
| **Token theft** | High | Short-lived access tokens, HTTP-only refresh cookies |
| **Email deliverability** | Medium | Use established SMTP service (SendGrid, Mailgun) |

---

## Success Metrics

**Technical:**
- 99.9% uptime
- < 100ms API response time (p95)
- < 2s sync time for 100 todos
- 80%+ test coverage
- Zero critical security vulnerabilities

**User Experience:**
- Seamless localStorage → cloud migration
- Real-time sync < 500ms
- Support 1000+ concurrent WebSocket connections
- Offline mode works indefinitely

---

## Future Enhancements

**Not in MVP, consider for v2:**
- Shared todo lists (collaboration)
- Todo categories/tags
- Recurring todos
- Attachments/images
- Mobile apps (React Native)
- Search with full-text indexing
- Analytics dashboard
- Admin panel
- API rate limiting per user tier
- GraphQL alternative to REST

---

## Questions & Decisions Log

**Q: Why SQLAlchemy instead of raw SQL?**  
A: ORM flexibility (SQLite dev → PostgreSQL prod), type safety, migrations with Alembic

**Q: Why JWT instead of sessions?**  
A: Stateless, scales horizontally, works with WebSockets, mobile-friendly

**Q: Why WebSockets instead of polling?**  
A: Lower latency, better UX, reduced server load, bi-directional

**Q: Why soft delete instead of hard delete?**  
A: Undo functionality, sync history, data recovery, audit trail

**Q: Why optimistic locking instead of pessimistic?**  
A: Better performance, conflicts are rare in single-user todos, simpler implementation

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/)
- [OAuth 2.0 RFC](https://datatracker.ietf.org/doc/html/rfc6749)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)

---

**Design Status:** ✅ Complete - Ready for Implementation  
**Next Step:** Begin Phase 1 implementation or create git worktree for isolated development
