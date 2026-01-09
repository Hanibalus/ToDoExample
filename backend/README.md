# FastAPI Backend - Phase 1 Implementation

## Project Setup

```bash
# Install dependencies
cd backend
poetry install

# Create .env file
cp .env.example .env

# Run development server
poetry run uvicorn app.main:app --reload

# Run tests
poetry run pytest -v
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout

### Todos
- `GET /api/v1/todos` - List todos
- `POST /api/v1/todos` - Create todo
- `GET /api/v1/todos/{id}` - Get single todo
- `PATCH /api/v1/todos/{id}` - Update todo
- `DELETE /api/v1/todos/{id}` - Delete todo
- `POST /api/v1/todos/{id}/restore` - Restore deleted todo
- `POST /api/v1/todos/bulk` - Bulk create todos
- `POST /api/v1/todos/sync` - Sync with conflict resolution

### Users
- `GET /api/v1/users/me` - Get current user
- `PATCH /api/v1/users/me` - Update profile
- `DELETE /api/v1/users/me` - Delete account

## Testing

```bash
# Run all tests
poetry run pytest -v

# Run with coverage
poetry run pytest -v --cov=app

# Run specific test file
poetry run pytest tests/test_auth.py -v

# Run specific test
poetry run pytest tests/test_auth.py::test_register -v
```

## Docker

```bash
# Development with auto-reload
docker-compose up api

# Run tests in Docker
docker-compose run test
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── database.py          # SQLAlchemy setup
│   ├── models.py            # ORM models
│   ├── schemas.py           # Pydantic schemas
│   ├── deps.py              # Dependencies
│   ├── core/
│   │   └── security.py      # JWT and password hashing
│   └── api/
│       ├── auth.py          # Auth endpoints
│       ├── todos.py         # Todo endpoints
│       └── users.py         # User endpoints
├── tests/
│   ├── conftest.py          # Pytest fixtures
│   ├── test_auth.py
│   ├── test_todos.py
│   └── test_health.py
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   └── docker-compose.yml
├── pyproject.toml           # Dependencies
└── .env.example             # Environment template
```

## Database

SQLite used for development, supports migration to PostgreSQL via `DATABASE_URL` in `.env`.

## Next Steps

- Phase 2: WebSocket support and sync
- Phase 3: OAuth integration
- Phase 4: Frontend integration
- Phase 5: Production deployment
