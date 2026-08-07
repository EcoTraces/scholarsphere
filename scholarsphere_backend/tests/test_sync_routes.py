from collections.abc import AsyncIterator
from datetime import timedelta
from unittest.mock import Mock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.routes import external_opportunities
from app.core.auth import AuthenticatedUser, get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import OpportunitySource, OpportunitySyncHistory
from app.models.external_opportunity import SyncStatus
from app.services.parsing import utc_now
from app.services.source_registry import seed_opportunity_sources


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
        async with database_session.begin():
            await seed_opportunity_sources(database_session)
        yield database_session
    await engine.dispose()


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
@pytest.mark.parametrize(
    "role", ["verificationOfficer", "administrator", "superAdministrator"]
)
async def test_sync_endpoint_queues_task_and_creates_history(
    role: str,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queued = Mock()
    monkeypatch.setattr(external_opportunities, "queue_source_sync", queued)
    overrides(session, role)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/external-opportunities/grants-gov/sync"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["source"] == "grants-gov"
    assert body["task_id"]
    assert body["correlation_id"]
    history = await session.scalar(
        select(OpportunitySyncHistory).where(
            OpportunitySyncHistory.task_id == body["task_id"]
        )
    )
    assert history.status == SyncStatus.queued
    assert history.triggered_by == f"{role}-user"
    queued.assert_called_once()


@pytest.mark.asyncio
async def test_sync_endpoint_denies_applicant(session: AsyncSession) -> None:
    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/external-opportunities/grants-gov/sync"
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403


def test_sync_endpoint_requires_authentication() -> None:
    response = TestClient(app).post(
        "/api/v1/external-opportunities/grants-gov/sync"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_source_health_and_static_routes_are_not_intercepted(
    session: AsyncSession,
) -> None:
    source = await session.scalar(
        select(OpportunitySource).where(
            OpportunitySource.source_code == "grants_gov"
        )
    )
    source.last_successful_sync_at = utc_now()
    source.last_failed_sync_at = utc_now() - timedelta(days=1)
    await session.commit()
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            health = await client.get("/api/v1/external-opportunities/health")
            sources = await client.get("/api/v1/external-opportunities/sources")
            history = await client.get(
                "/api/v1/external-opportunities/sync-history"
            )
            pending = await client.get(
                "/api/v1/external-opportunities/pending-verification"
            )
    finally:
        app.dependency_overrides.clear()

    assert health.status_code == 200
    grants_health = next(
        item for item in health.json() if item["source_code"] == "grants_gov"
    )
    assert grants_health["active_status"] is True
    assert grants_health["last_successful_sync"] is not None
    assert sources.status_code == 200
    assert history.status_code == 200
    assert "items" in history.json()
    assert pending.status_code == 200
    assert "items" in pending.json()


@pytest.mark.asyncio
async def test_sync_history_filters_and_paginates(session: AsyncSession) -> None:
    source = await session.scalar(
        select(OpportunitySource).where(
            OpportunitySource.source_code == "grants_gov"
        )
    )
    await session.commit()
    async with session.begin():
        for index in range(3):
            session.add(
                OpportunitySyncHistory(
                    task_id=f"task-{index}",
                    source_id=source.id,
                    source_code="grants_gov",
                    started_at=utc_now() - timedelta(hours=index),
                    status=SyncStatus.completed,
                    correlation_id=f"correlation-{index}",
                    triggered_by="officer-1",
                )
            )
    overrides(session, "administrator")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/external-opportunities/sync-history",
                params={
                    "source": "grants-gov",
                    "status": "completed",
                    "triggered_by": "officer-1",
                    "page": 2,
                    "page_size": 2,
                    "sort_direction": "asc",
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 1


@pytest.mark.asyncio
async def test_queue_failure_marks_history_failed_without_secret(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_queue(*args, **kwargs):
        raise RuntimeError("redis://user:secret@host")

    monkeypatch.setattr(external_opportunities, "queue_source_sync", fail_queue)
    overrides(session, "administrator")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/external-opportunities/grants-gov/sync"
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert "secret" not in response.text
    assert (
        await session.scalar(
            select(func.count(OpportunitySyncHistory.id)).where(
                OpportunitySyncHistory.status == SyncStatus.failed
            )
        )
        == 1
    )
