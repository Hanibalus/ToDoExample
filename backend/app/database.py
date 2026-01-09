from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
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
