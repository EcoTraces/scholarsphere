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


async def _seed_reverification_due_opportunity(
    factory: async_sessionmaker[AsyncSession], *, external_id: str = "reverify-1"
) -> str:
    from app.models import ExternalOpportunity, OpportunitySource
    from app.models.external_opportunity import PublicationStatus, VerificationStatus
    from app.services.parsing import utc_now

    async with factory() as session:
        async with session.begin():
            source = OpportunitySource(
                source_code="grants_gov",
                source_name="Grants.gov",
                source_type="api",
                base_url="https://api.grants.gov/v1/api",
                authentication_type="none",
                trust_level="official",
            )
            session.add(source)
            await session.flush()
            now = utc_now()
            opportunity = ExternalOpportunity(
                source_id=source.id,
                external_id=external_id,
                title="Community Resilience Grant",
                opportunity_type="grant",
                provider_name="Department of Resilience",
                opportunity_status="posted",
                payload_hash="hash",
                external_fingerprint="fingerprint",
                verification_status=VerificationStatus.reverification_required,
                publication_status=PublicationStatus.unpublished,
                collected_at=now,
                last_external_update_at=now,
            )
            session.add(opportunity)
            await session.flush()
            return str(opportunity.id)


async def _seed_officer_history(
    factory: async_sessionmaker[AsyncSession], *, actor_id: str = "officer-1"
) -> None:
    from app.models import ImportAuditLog
    from app.services.parsing import utc_now

    async with factory() as session:
        async with session.begin():
            session.add(
                ImportAuditLog(
                    actor_id=actor_id,
                    actor_role="verificationOfficer",
                    action="verification_approved",
                    entity_type="external_opportunity",
                    entity_id="some-other-opportunity",
                    correlation_id="seed-correlation",
                )
            )


@pytest.mark.asyncio
async def test_reverification_reminders_creates_a_real_in_app_notification(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    from app.models.notification import ScholarSphereNotification

    await _seed_reverification_due_opportunity(task_database)
    await _seed_officer_history(task_database, actor_id="officer-1")

    result = await opportunity_sync._send_reverification_reminders()

    assert result == {
        "opportunities_due": 1,
        "recipients": 1,
        "reminders_created": 1,
    }
    async with task_database() as session:
        rows = (await session.scalars(select(ScholarSphereNotification))).all()
    assert len(rows) == 1
    notification = rows[0]
    assert notification.user_id == "officer-1"
    assert notification.type == "reverification_due"
    assert notification.channels == ["in_app"]
    assert notification.status.value == "scheduled"
    assert "Community Resilience Grant" in notification.message


@pytest.mark.asyncio
async def test_reverification_reminders_are_not_duplicated_on_rerun(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    from app.models.notification import ScholarSphereNotification

    await _seed_reverification_due_opportunity(task_database)
    await _seed_officer_history(task_database, actor_id="officer-1")

    first = await opportunity_sync._send_reverification_reminders()
    second = await opportunity_sync._send_reverification_reminders()

    assert first["reminders_created"] == 1
    assert second["reminders_created"] == 0
    async with task_database() as session:
        rows = (await session.scalars(select(ScholarSphereNotification))).all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_reverification_reminders_respect_disabled_preferences(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    from app.models.notification import (
        NotificationFrequency,
        NotificationPreferences,
        ScholarSphereNotification,
    )

    await _seed_reverification_due_opportunity(task_database)
    await _seed_officer_history(task_database, actor_id="officer-1")
    async with task_database() as session:
        async with session.begin():
            session.add(
                NotificationPreferences(
                    user_id="officer-1",
                    channels=["in_app", "email"],
                    frequency=NotificationFrequency.disabled,
                    reminder_days=[30, 14, 7, 3, 1],
                )
            )

    result = await opportunity_sync._send_reverification_reminders()

    assert result["reminders_created"] == 0
    async with task_database() as session:
        rows = (await session.scalars(select(ScholarSphereNotification))).all()
    assert rows == []


@pytest.mark.asyncio
async def test_reverification_reminders_report_zero_recipients_honestly(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    # No officer has ever taken a real verification action in this
    # database - the task must not fabricate a recipient list, it should
    # report the real due count with zero reminders sent.
    await _seed_reverification_due_opportunity(task_database)

    result = await opportunity_sync._send_reverification_reminders()

    assert result == {
        "opportunities_due": 1,
        "recipients": 0,
        "reminders_created": 0,
    }
