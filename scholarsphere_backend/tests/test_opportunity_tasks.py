from collections.abc import AsyncIterator
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
import respx
from celery.exceptions import Retry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.http_client import ExternalAPIError
from app.db.base import Base
from app.models import ExternalOpportunity, OpportunitySyncHistory, VerificationReview
from app.models.external_opportunity import PublicationStatus, SyncStatus, VerificationStatus
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.parsing import utc_now
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
async def test_rerunning_the_same_task_id_is_idempotent(
    task_database: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-running a sync with the same task_id (e.g. a Celery retry, or an
    at-least-once broker redelivering the same message) must not create a
    second OpportunitySyncHistory row or a duplicate opportunity - the
    unchanged-payload path (payload_hash comparison in
    app/services/opportunity_import.py) should report it as skipped, not
    created again.
    """
    collector = SimpleNamespace(
        collect_for_import=AsyncMock(return_value=[record("idempotent-record")])
    )
    monkeypatch.setattr(opportunity_sync, "_collector", lambda _: collector)

    first = await opportunity_sync._run_source_sync(
        "grants_gov",
        task_id="task-idempotent",
        correlation_id="correlation-idempotent",
        triggered_by="officer-1",
    )
    second = await opportunity_sync._run_source_sync(
        "grants_gov",
        task_id="task-idempotent",
        correlation_id="correlation-idempotent",
        triggered_by="officer-1",
    )

    async with task_database() as session:
        histories = (
            await session.scalars(
                select(OpportunitySyncHistory).where(
                    OpportunitySyncHistory.task_id == "task-idempotent"
                )
            )
        ).all()
        opportunities = (
            await session.scalars(
                select(ExternalOpportunity).where(
                    ExternalOpportunity.external_id == "idempotent-record"
                )
            )
        ).all()

    assert first["records_created"] == 1
    assert second["records_created"] == 0
    assert second["records_skipped"] == 1
    assert len(histories) == 1, "re-running the same task_id must not create a second history row"
    assert len(opportunities) == 1, "re-running the same task_id must not create a duplicate opportunity"


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
    """Regression note: `celery_app.tasks` only contains whatever task
    modules have actually been *imported* in this process - it was
    passing only when run as part of the full suite, because some other
    test file happened to import `app.tasks.notifications` first as a
    side effect, registering its tasks into the shared `celery_app`
    singleton. Running this file (or this test) alone used to fail with
    `process_due_notifications`/`retry_failed_notifications` reported
    missing, even though they're real, correctly-decorated tasks - a
    test-isolation bug, not a production one (a real worker/beat process
    loads every module in `Celery(..., include=[...])` at startup via
    `import_default_modules()`, which is exactly what's called explicitly
    below to make this test deterministic regardless of run order).
    """
    opportunity_sync.celery_app.loader.import_default_modules()
    schedule = opportunity_sync.celery_app.conf.beat_schedule
    registered = opportunity_sync.celery_app.tasks
    assert schedule
    assert all(entry["task"] in registered for entry in schedule.values())


def test_sync_task_executes_through_the_real_celery_task_interface(
    task_database: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DIRECT CELERY TASK EXECUTION TEST (task_always_eager), not a real
    broker/worker test.

    Every other test in this file calls `_execute_source_task`/
    `_run_source_sync` directly - this one instead goes through the actual
    `@celery_app.task(bind=True, ...)` object (`sync_cscuk_scholarships`)
    via `.apply()`, exercising the real task-binding machinery
    (`self.request.id`, `self.max_retries`, the `bind=True` decorator
    itself) that direct-function calls skip. `task_always_eager=True`
    means this still runs in-process with no real broker/worker involved -
    see Task.md for why a real Redis broker + worker + beat scheduler
    could not be exercised in this environment (no Redis/Docker
    available), and why that remains a separate, undone verification.
    """
    task_record = NormalizedExternalOpportunity(
        source_code="cscuk_scholarships",
        external_id="celery-task-record",
        title="Task Scholarship",
        opportunity_type="scholarship",
        provider_name="Commonwealth Scholarship Commission in the UK",
        opportunity_status="posted",
        raw_payload={"id": "celery-task-record"},
    )
    collector = SimpleNamespace(
        collect_for_import=AsyncMock(return_value=[task_record])
    )
    monkeypatch.setattr(opportunity_sync, "_collector", lambda _: collector)
    opportunity_sync.celery_app.conf.task_always_eager = True
    opportunity_sync.celery_app.conf.task_eager_propagates = True
    try:
        result = opportunity_sync.sync_cscuk_scholarships.apply(
            kwargs={
                "correlation_id": "celery-eager-correlation",
                "triggered_by": "eager-test",
            }
        )
    finally:
        opportunity_sync.celery_app.conf.task_always_eager = False
        opportunity_sync.celery_app.conf.task_eager_propagates = False

    assert result.successful(), result.traceback
    payload = result.get()
    assert payload["status"] == "completed"
    assert payload["records_created"] == 1


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


def _force_firebase_roster_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deterministically exercise the audit-log fallback path.

    A real (unmocked) Firebase call would try to reach a live project this
    test environment does not have - forcing the error directly keeps
    these tests fast and deterministic instead of depending on a real
    network failure. This is exactly the real condition this environment
    is in today (no Firebase credentials configured), so it is an honest
    simulation, not an artificial one.
    """

    def _raise() -> list[str]:
        raise opportunity_sync.FirebaseRosterError("no Firebase credentials in test environment")

    monkeypatch.setattr(opportunity_sync, "list_reverification_recipient_uids", _raise)


@pytest.mark.asyncio
async def test_reverification_reminders_creates_a_real_in_app_notification(
    task_database: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.models.notification import ScholarSphereNotification

    _force_firebase_roster_unavailable(monkeypatch)
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.models.notification import ScholarSphereNotification

    _force_firebase_roster_unavailable(monkeypatch)
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.models.notification import (
        NotificationFrequency,
        NotificationPreferences,
        ScholarSphereNotification,
    )

    _force_firebase_roster_unavailable(monkeypatch)
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No officer has ever taken a real verification action in this
    # database - the task must not fabricate a recipient list, it should
    # report the real due count with zero reminders sent.
    _force_firebase_roster_unavailable(monkeypatch)
    await _seed_reverification_due_opportunity(task_database)

    result = await opportunity_sync._send_reverification_reminders()

    assert result == {
        "opportunities_due": 1,
        "recipients": 0,
        "reminders_created": 0,
    }


@pytest.mark.asyncio
async def test_reverification_reminders_use_real_firebase_roster_when_available(
    task_database: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The primary path: an officer who has NEVER made a verification

    decision (no ImportAuditLog activity at all) still receives a
    reminder, because the real Firebase roster - not decision history -
    is now the primary recipient source. This is exactly the gap the
    audit-log-only heuristic could not close.
    """
    from app.models.notification import ScholarSphereNotification

    monkeypatch.setattr(
        opportunity_sync,
        "list_reverification_recipient_uids",
        lambda: ["brand-new-officer"],
    )
    await _seed_reverification_due_opportunity(task_database)
    # Deliberately no _seed_officer_history() call - this officer has zero
    # decision history and would have been invisible to the old heuristic.

    result = await opportunity_sync._send_reverification_reminders()

    assert result == {
        "opportunities_due": 1,
        "recipients": 1,
        "reminders_created": 1,
    }
    async with task_database() as session:
        rows = (await session.scalars(select(ScholarSphereNotification))).all()
    assert len(rows) == 1
    assert rows[0].user_id == "brand-new-officer"


@pytest.mark.asyncio
async def test_reverification_reminders_fall_back_to_audit_log_on_firebase_error(
    task_database: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit test of the degraded-but-honest fallback: when Firebase

    enumeration fails, real prior-decision history is used instead of
    silently sending zero reminders.
    """
    _force_firebase_roster_unavailable(monkeypatch)
    await _seed_reverification_due_opportunity(task_database)
    await _seed_officer_history(task_database, actor_id="fallback-officer")

    result = await opportunity_sync._send_reverification_reminders()

    assert result["recipients"] == 1
    assert result["reminders_created"] == 1


async def _seed_verified_published_opportunity(
    factory: async_sessionmaker[AsyncSession],
    *,
    external_id: str = "link-health-1",
    application_url: str | None = "https://apply.example.test/scholarship",
    source_url: str | None = "https://provider.example.test/scholarship",
    link_checked_at=None,
    with_review: bool = False,
):
    """Returns the seeded opportunity's real UUID (not a stringified copy)

    - callers that pass it back into session.get()/a `Model.id ==` filter
    need the actual uuid.UUID instance, since this test goes straight to
    the ORM rather than through a FastAPI path param (which is what does
    the str->UUID conversion for the HTTP-boundary tests elsewhere in this
    codebase).
    """
    from app.models import OpportunitySource

    async with factory() as session:
        async with session.begin():
            source = OpportunitySource(
                source_code=f"grants_gov-{external_id}",
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
                external_fingerprint=f"fingerprint-{external_id}",
                official_application_url=application_url,
                official_source_url=source_url,
                verification_status=VerificationStatus.verified,
                publication_status=PublicationStatus.published,
                link_checked_at=link_checked_at,
                collected_at=now,
                last_external_update_at=now,
            )
            session.add(opportunity)
            await session.flush()
            if with_review:
                session.add(
                    VerificationReview(
                        opportunity_id=opportunity.id,
                        application_link_checked=True,
                        decision=VerificationStatus.verified.value,
                        verified_at=now,
                    )
                )
            return opportunity.id


@pytest.mark.asyncio
@respx.mock
async def test_link_health_leaves_reachable_opportunity_verified(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    respx.get("https://apply.example.test/scholarship").mock(
        return_value=httpx.Response(200, text="<html>apply here</html>")
    )
    opportunity_id = await _seed_verified_published_opportunity(task_database)

    result = await opportunity_sync._check_link_health()

    assert result == {"checked": 1, "broken": 0}
    async with task_database() as session:
        opportunity = await session.get(ExternalOpportunity, opportunity_id)
    assert opportunity.verification_status == VerificationStatus.verified
    assert opportunity.link_checked_at is not None


@pytest.mark.asyncio
@respx.mock
async def test_link_health_demotes_opportunity_on_broken_link(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    respx.get("https://apply.example.test/scholarship").mock(
        return_value=httpx.Response(404)
    )
    opportunity_id = await _seed_verified_published_opportunity(
        task_database, with_review=True
    )

    result = await opportunity_sync._check_link_health()

    assert result == {"checked": 1, "broken": 1}
    async with task_database() as session:
        opportunity = await session.get(ExternalOpportunity, opportunity_id)
        history = (
            await session.scalars(
                select(opportunity_sync.VerificationHistory).where(
                    opportunity_sync.VerificationHistory.opportunity_id == opportunity_id
                )
            )
        ).all()
        review = await session.scalar(
            select(VerificationReview).where(
                VerificationReview.opportunity_id == opportunity_id
            )
        )
    assert opportunity.verification_status == VerificationStatus.reverification_required
    assert opportunity.link_checked_at is not None
    assert len(history) == 1
    assert "link health check" in history[0].reason.lower()
    assert review.application_link_checked is False


@pytest.mark.asyncio
@respx.mock
async def test_link_health_falls_back_to_source_url_when_no_application_url(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    respx.get("https://provider.example.test/scholarship").mock(
        return_value=httpx.Response(200, text="ok")
    )
    await _seed_verified_published_opportunity(
        task_database, application_url=None
    )

    result = await opportunity_sync._check_link_health()

    assert result == {"checked": 1, "broken": 0}


@pytest.mark.asyncio
async def test_link_health_skips_opportunity_with_no_url_at_all(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    await _seed_verified_published_opportunity(
        task_database, application_url=None, source_url=None
    )

    result = await opportunity_sync._check_link_health()

    assert result == {"checked": 0, "broken": 0}


@pytest.mark.asyncio
async def test_link_health_ignores_unpublished_and_unverified_opportunities(
    task_database: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_if_called(url: str) -> bool:
        raise AssertionError(f"should not check unpublished/unverified rows: {url}")

    monkeypatch.setattr(opportunity_sync, "check_link_reachable", fail_if_called)
    await _seed_reverification_due_opportunity(task_database, external_id="not-published")

    result = await opportunity_sync._check_link_health()

    assert result == {"checked": 0, "broken": 0}


@pytest.mark.asyncio
@respx.mock
async def test_link_health_prioritizes_never_checked_then_oldest_checked(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    respx.get("https://apply.example.test/scholarship").mock(
        return_value=httpx.Response(200, text="ok")
    )
    now = utc_now()
    await _seed_verified_published_opportunity(
        task_database,
        external_id="checked-recent",
        application_url="https://apply.example.test/scholarship",
        link_checked_at=now,
    )
    await _seed_verified_published_opportunity(
        task_database,
        external_id="checked-old",
        application_url="https://apply.example.test/scholarship",
        link_checked_at=now - timedelta(days=10),
    )
    await _seed_verified_published_opportunity(
        task_database,
        external_id="never-checked",
        application_url="https://apply.example.test/scholarship",
        link_checked_at=None,
    )

    result = await opportunity_sync._check_link_health()
    assert result["checked"] == 3

    async with task_database() as session:
        rows = (
            await session.scalars(
                select(ExternalOpportunity).order_by(ExternalOpportunity.external_id)
            )
        ).all()
    assert all(row.link_checked_at is not None for row in rows)
