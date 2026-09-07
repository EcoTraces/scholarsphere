from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()
connect_args: dict[str, object] = {}
if settings.database_url.startswith("postgresql"):
    # Neon's pooled (PgBouncer transaction-mode) connection string breaks
    # asyncpg's default server-side prepared statement cache, since a pooled
    # connection can be handed to a different logical session between
    # statements. Disabling the cache is the documented fix and is a no-op
    # (mild perf cost only) against a direct/non-pooled connection too.
    connect_args["statement_cache_size"] = 0

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args=connect_args,
)
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    await engine.dispose()

