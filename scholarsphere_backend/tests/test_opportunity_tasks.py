from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from celery.exceptions import Retry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.http_client import ExternalAPIError
from app.db.base import Base
from app.models import OpportunitySyncHistory
from app.models.external_opportunity import SyncStatus
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.tasks import opportunity_sync


@pytest_asyncio.fixture
async def task_database(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(opportunity_sync, "AsyncSessionFactory", factory)
    yield factory
    await engine.dispose()


def record(external_id: str = "task-record") -> NormalizedExternalOpportunity:
    return NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id=external_id,
        title="Task Grant",
        opportunity_type="grant",
        provider_name="Agency",
        opportunity_status="posted",
        raw_payload={"id": external_id},
    )


@pytest.mark.asyncio
async def test_task_records_running_completed_and_statistics(
    task_database: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[SyncStatus] = []

    async def collect_for_import():
        async with task_database() as session:
            history = await session.scalar(
                select(OpportunitySyncHistory).where(
                    OpportunitySyncHistory.task_id == "task-complete"
                )
            )
            observed.append(history.status)
        return [record()]

    collector = SimpleNamespace(collect_for_import=collect_for_import)
    monkeypatch.setattr(opportunity_sync, "_collector", lambda _: collector)
    result = await opportunity_sync._run_source_sync(
        "grants_gov",
        task_id="task-complete",
        correlation_id="correlation-complete",
        triggered_by="officer-1",
    )

    async with task_database() as session:
        history = await session.scalar(
            select(OpportunitySyncHistory).where(
                OpportunitySyncHistory.task_id == "task-complete"
            )
        )
    assert observed == [SyncStatus.running]
    assert history.status == SyncStatus.completed
    assert history.records_received == 1
    assert history.records_created == 1
    assert history.finished_at is not None
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_partial_failure_sets_partially_completed(
    task_database: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = record("invalid").model_dump()
    invalid["title"] = ""
    collector = SimpleNamespace(
        collect_for_import=AsyncMock(return_value=[record("valid"), invalid])
    )
    monkeypatch.setattr(opportunity_sync, "_collector", lambda _: collector)
    result = await opportunity_sync._run_source_sync(
        "grants_gov",
        task_id="task-partial",
        correlation_id="correlation-partial",
        triggered_by=None,
    )
    async with task_database() as session:
        history = await session.scalar(
            select(OpportunitySyncHistory).where(
                OpportunitySyncHistory.task_id == "task-partial"
            )
        )
    assert result["status"] == "partially_completed"
    assert history.status == SyncStatus.partially_completed
    assert history.records_created == 1
    assert history.records_failed == 1


@pytest.mark.asyncio
async def test_failed_state_uses_safe_error_summary(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    async with task_database() as session:
        async with session.begin():
            sources = await opportunity_sync.seed_opportunity_sources(session)
            session.add(
                OpportunitySyncHistory(
                    task_id="task-failed",
                    source_id=sources["grants_gov"].id,
                    source_code="grants_gov",
                    started_at=opportunity_sync.utc_now(),
                    correlation_id="correlation-failed",
                    status=SyncStatus.running,
                )
            )
    await opportunity_sync._mark_failed(
        "task-failed", "grants_gov", RuntimeError("api-key=secret")
    )
    async with task_database() as session:
        history = await session.scalar(
            select(OpportunitySyncHistory).where(
                OpportunitySyncHistory.task_id == "task-failed"
            )
        )
    assert history.status == SyncStatus.failed
    assert "secret" not in history.error_summary


def test_temporary_failure_retries_with_a_bound_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary = ExternalAPIError("Rate limited.", status_code=429)
    calls = iter([temporary, None])

    def run(awaitable):
        value = next(calls)
        awaitable.close()
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(opportunity_sync, "run_async_safely", run)
    task = SimpleNamespace(
        request=SimpleNamespace(id="retry-task", retries=0),
        max_retries=3,
        retry=lambda **kwargs: Retry(),
    )
    with pytest.raises(Retry):
        opportunity_sync._execute_source_task(
            task, "grants_gov", "correlation", None
        )


def test_permanent_failure_does_not_retry_indefinitely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    permanent = ExternalAPIError("Rejected request.", status_code=400)
    calls = iter([permanent, None])

    def run(awaitable):
        value = next(calls)
        awaitable.close()
        if isinstance(value, Exception):
            raise value
        return value

    retry = AsyncMock()
    monkeypatch.setattr(opportunity_sync, "run_async_safely", run)
    task = SimpleNamespace(
        request=SimpleNamespace(id="permanent-task", retries=0),
        max_retries=3,
        retry=retry,
    )
    with pytest.raises(ExternalAPIError):
        opportunity_sync._execute_source_task(
            task, "grants_gov", "correlation", None
        )
    retry.assert_not_called()


def test_all_scheduled_task_names_resolve() -> None:
    schedule = opportunity_sync.celery_app.conf.beat_schedule
    registered = opportunity_sync.celery_app.tasks
    assert schedule
    assert all(entry["task"] in registered for entry in schedule.values())
