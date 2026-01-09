import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db_session
from app.config import settings

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function")
async def test_db():
    """Create test database"""
    engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=False,
        future=True
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, future=True
    )
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
def client(test_db):
    """Test client with test database"""
    def override_get_db():
        return test_db
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Test user credentials"""
    return {
        "email": "test@example.com",
        "password": "TestPass123!",
        "display_name": "Test User"
    }


@pytest.fixture
async def auth_token(client, test_user_data):
    """Register and get auth token"""
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Authorization headers with token"""
    return {"Authorization": f"Bearer {auth_token}"}
