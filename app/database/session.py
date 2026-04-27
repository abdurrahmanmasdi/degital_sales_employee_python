"""
Async database session management using SQLAlchemy 2.0.

Provides AsyncEngine, async_sessionmaker, and a FastAPI dependency
for injecting async database sessions into routes.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from app.core.config import settings


# Create async engine with connection pooling optimized for production.
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL query logging during development
    future=True,
    pool_size=10,  # Number of connections to keep in the pool
    max_overflow=20,  # Additional connections allowed beyond pool_size
    pool_pre_ping=True,  # Test connections before using them
    connect_args={
        "timeout": 10,
        "server_settings": {
            "application_name": "ai_sales_agent",
            "jit": "off",
        }
    },
)

# Create an async session factory bound to the engine.
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency function for injecting async database sessions.
    
    Yields an AsyncSession that can be used in route handlers.
    The session is automatically closed after the route completes.
    
    Example usage in a route:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    
    Yields:
        AsyncSession: An async SQLAlchemy session.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
