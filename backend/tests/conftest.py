import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db_session

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
def client():
    """Test client with test database override"""
    
    # Create the test database and session factory
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False, future=True)
    
    # Create tables
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    # Run async setup
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(create_tables())
    
    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, future=True
    )
    
    async def override_get_db():
        async with async_session_factory() as session:
            yield session
    
    # Override the dependency
    app.dependency_overrides[get_db_session] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup
    app.dependency_overrides.clear()
    
    # Drop tables
    async def drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
    
    loop.run_until_complete(drop_tables())


@pytest.fixture
def test_user_data():
    """Test user credentials"""
    return {
        "email": "test@example.com",
        "password": "TestPass123!",
        "display_name": "Test User"
    }


@pytest.fixture
def auth_token(client, test_user_data):
    """Register and get auth token"""
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Authorization headers with token"""
    return {"Authorization": f"Bearer {auth_token}"}
