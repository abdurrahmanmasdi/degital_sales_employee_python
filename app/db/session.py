from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

# 1. Create the robust Async Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True if you want to see raw SQL queries in your terminal
    future=True,
    pool_pre_ping=True, 
)

# 2. Create the Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 3. The FastAPI Dependency 
# We will inject this into our webhooks to get a fresh, safe database connection per request.
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()