"""Tests for GET /api/v1/scraper-metrics (app/api/routes/scraper_metrics.py)."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.scraper_metrics import get_metrics


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()
    app.dependency_overrides.clear()


def user(role: str) -> AuthenticatedUser:
    return AuthenticatedUser(
        uid=f"{role}-user",
        email=f"{role}@example.test",
        email_verified=True,
        role=role,
        permissions=frozenset(),
    )


def overrides(session: AsyncSession, role: str) -> None:
    async def current_user() -> AuthenticatedUser:
        return user(role)

    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


@pytest.mark.asyncio
async def test_requires_staff_role(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/scraper-metrics")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_administrator_can_read_metrics_snapshot(session: AsyncSession) -> None:
    overrides(session, "administrator")
    metrics = get_metrics()
    metrics.reset()
    metrics.increment("http_attempts", by=10)
    metrics.increment("browser_fallbacks", by=3)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/scraper-metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["http_attempts"] == 10
    assert body["browser_fallbacks"] == 3
    assert body["browser_fallback_rate"] == pytest.approx(0.3)
    # An untouched ratio must come back null, never a fabricated 0.0.
    assert body["duplicate_rate"] is None
