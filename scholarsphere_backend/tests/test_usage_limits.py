"""Unit tests for app/services/usage_limits.py - configurable AI usage

ceilings, per the platform spec's "Usage Management" requirement.
"""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.models.premium_billing import AIUsageStatus, UsageLimit
from app.services.usage_limits import UsageLimitExceededError, check_usage_allowed, record_usage


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_allows_usage_under_the_default_daily_limit(session: AsyncSession) -> None:
    settings = Settings(ai_usage_daily_limit_default=3, ai_usage_monthly_limit_default=100)
    for _ in range(2):
        await record_usage(
            session,
            user_id="user-1",
            feature="sop",
            provider="openai",
            model="gpt-test",
            tokens_used=10,
            status=AIUsageStatus.success,
        )
    await check_usage_allowed(session, user_id="user-1", feature="sop", settings=settings)


@pytest.mark.asyncio
async def test_denies_usage_once_daily_limit_reached(session: AsyncSession) -> None:
    settings = Settings(ai_usage_daily_limit_default=2, ai_usage_monthly_limit_default=100)
    for _ in range(2):
        await record_usage(
            session,
            user_id="user-1",
            feature="sop",
            provider="openai",
            model="gpt-test",
            tokens_used=10,
            status=AIUsageStatus.success,
        )
    with pytest.raises(UsageLimitExceededError) as excinfo:
        await check_usage_allowed(session, user_id="user-1", feature="sop", settings=settings)
    assert excinfo.value.period == "day"


@pytest.mark.asyncio
async def test_usage_is_isolated_per_user_and_feature(session: AsyncSession) -> None:
    settings = Settings(ai_usage_daily_limit_default=1, ai_usage_monthly_limit_default=100)
    await record_usage(
        session,
        user_id="user-1",
        feature="sop",
        provider="openai",
        model="gpt-test",
        tokens_used=10,
        status=AIUsageStatus.success,
    )
    # A different user is unaffected.
    await check_usage_allowed(session, user_id="user-2", feature="sop", settings=settings)
    # A different feature for the same user is unaffected.
    await check_usage_allowed(session, user_id="user-1", feature="cv_polish", settings=settings)
    with pytest.raises(UsageLimitExceededError):
        await check_usage_allowed(session, user_id="user-1", feature="sop", settings=settings)


@pytest.mark.asyncio
async def test_admin_configured_usage_limit_row_overrides_default(session: AsyncSession) -> None:
    settings = Settings(ai_usage_daily_limit_default=1000, ai_usage_monthly_limit_default=1000)
    session.add(UsageLimit(feature="sop", plan_code=None, limit_per_day=1, limit_per_month=100))
    await session.commit()

    await record_usage(
        session,
        user_id="user-1",
        feature="sop",
        provider="openai",
        model="gpt-test",
        tokens_used=10,
        status=AIUsageStatus.success,
    )
    with pytest.raises(UsageLimitExceededError):
        await check_usage_allowed(session, user_id="user-1", feature="sop", settings=settings)
