from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=900,
    connect_args={
        "statement_cache_size": 0,
        "server_settings": {
            "application_name": "postx",
            "statement_timeout": "30000",
            "idle_in_transaction_session_timeout": "30000",
        },
    },
)

SessionFactory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1"))
        return True
    except Exception:
        return False


async def close_database() -> None:
    await engine.dispose()
