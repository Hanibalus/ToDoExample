from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Handle both sync and async database URLs
database_url = settings.DATABASE_URL
if database_url.startswith("sqlite:///"):
    # Convert SQLite to async version
    database_url = "sqlite+aiosqlite:///" + database_url.replace("sqlite:///", "")

# Create async engine
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True
)

# Session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, future=True
)

# Base for models
Base = declarative_base()


async def get_db_session() -> AsyncSession:
    """Get database session"""
    async with async_session() as session:
        yield session
