import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, timedelta
from time import monotonic
from typing import Any, Coroutine, TypeVar
from uuid import uuid4

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError
from app.db.session import AsyncSessionFactory
from app.models import (
    ExternalOpportunity,
    OpportunitySource,
    OpportunitySyncHistory,
    RawExternalOpportunity,
    VerificationHistory,
    VerificationReview,
)
from app.models.external_opportunity import (
    ProcessingStatus,
    PublicationStatus,
    SyncStatus,
    VerificationStatus,
)
from app.services.eu_funding import EUFundingSource
from app.services.audit import append_audit
from app.services.grants_gov import GrantsGovSource
from app.services.opportunity_import import import_opportunities
from app.services.parsing import utc_now
from app.services.simpler_grants import SimplerGrantsSource
from app.services.source_registry import seed_opportunity_sources

logger = logging.getLogger(__name__)
settings = get_settings()
celery_app = Celery(
    "scholarsphere",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.opportunity_sync"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "sync-grants-gov": {
            "task": "app.tasks.opportunity_sync.sync_grants_gov",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "sync-simpler-grants": {
            "task": "app.tasks.opportunity_sync.sync_simpler_grants",
            "schedule": crontab(minute=20, hour="*/6"),
        },
        "sync-eu-funding": {
            "task": "app.tasks.opportunity_sync.sync_eu_funding",
            "schedule": crontab(minute=40, hour="*/12"),
        },
        "retry-failed-external-records": {
            "task": "app.tasks.opportunity_sync.retry_failed_records",
            "schedule": crontab(minute=10, hour="*/2"),
        },
        "detect-expired-opportunities": {
            "task": "app.tasks.opportunity_sync.detect_expired_opportunities",
            "schedule": crontab(minute=5, hour=1),
        },
        "schedule-reverification": {
            "task": "app.tasks.opportunity_sync.schedule_reverification",
            "schedule": crontab(minute=15, hour=2),
        },
        "send-reverification-reminders": {
            "task": "app.tasks.opportunity_sync.send_reverification_reminders",
            "schedule": crontab(minute=30, hour=8, day_of_week="1-5"),
        },
    },
)

T = TypeVar("T")
TEMPORARY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
SOURCE_TASK_NAMES = {
    "grants_gov": "app.tasks.opportunity_sync.sync_grants_gov",
    "simpler_grants": "app.tasks.opportunity_sync.sync_simpler_grants",
    "eu_funding_tenders": "app.tasks.opportunity_sync.sync_eu_funding",
}


def run_async_safely(awaitable: Coroutine[Any, Any, T]) -> T:
    """Run async persistence from a synchronous worker, even in eager async tests."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, awaitable).result()


def queue_source_sync(
    source_code: str,
    *,
    task_id: str,
    correlation_id: str,
    triggered_by: str,
) -> None:
    task_name = SOURCE_TASK_NAMES[source_code]
    celery_app.send_task(
        task_name,
        kwargs={
            "correlation_id": correlation_id,
            "triggered_by": triggered_by,
        },
        task_id=task_id,
    )


def _execute_source_task(
    task: Any,
    source_code: str,
    correlation_id: str | None,
    triggered_by: str | None,
) -> dict[str, Any]:
    task_id = task.request.id or str(uuid4())
    correlation = correlation_id or str(uuid4())
    try:
        return run_async_safely(
            _run_source_sync(
                source_code,
                task_id=task_id,
                correlation_id=correlation,
                triggered_by=triggered_by,
            )
        )
    except ExternalAPIError as error:
        temporary = error.status_code in TEMPORARY_STATUS_CODES or error.status_code is None
        event = "rate_limited" if error.status_code == 429 else "timeout_or_transport_failure"
        logger.warning(
            "%s source_code=%s task_id=%s correlation_id=%s",
            event,
            source_code,
            task_id,
            correlation,
        )
        if temporary and task.request.retries < task.max_retries:
            run_async_safely(_mark_retry(task_id, source_code, error))
            logger.warning(
                "sync_retry source_code=%s task_id=%s correlation_id=%s",
                source_code,
                task_id,
                correlation,
            )
            raise task.retry(exc=error, countdown=min(60 * 2**task.request.retries, 900))
        run_async_safely(_mark_failed(task_id, source_code, error))
        raise
    except Exception as error:
        run_async_safely(_mark_failed(task_id, source_code, error))
        raise


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_grants_gov",
    max_retries=3,
)
def sync_grants_gov(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "grants_gov", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_simpler_grants",
    max_retries=3,
)
def sync_simpler_grants(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "simpler_grants", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_eu_funding",
    max_retries=3,
)
def sync_eu_funding(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "eu_funding_tenders", correlation_id, triggered_by)


async def _run_source_sync(
    source_code: str,
    *,
    task_id: str,
    correlation_id: str,
    triggered_by: str | None,
) -> dict[str, Any]:
    started = monotonic()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            sources = await seed_opportunity_sources(session)
            source = sources[source_code]
            history = await session.scalar(
                select(OpportunitySyncHistory).where(
                    OpportunitySyncHistory.task_id == task_id
                )
            )
            if history is None:
                history = OpportunitySyncHistory(
                    task_id=task_id,
                    source_id=source.id,
                    source_code=source_code,
                    triggered_by=triggered_by,
                    correlation_id=correlation_id,
                    started_at=utc_now(),
                    status=SyncStatus.running,
                )
                session.add(history)
            else:
                history.started_at = utc_now()
                history.status = SyncStatus.running
            source.last_sync_at = history.started_at
            if not source.is_active:
                history.status = SyncStatus.cancelled
                history.finished_at = utc_now()
                history.error_summary = "The external source is inactive."

    if not source.is_active:
        logger.info(
            "sync_cancelled source_code=%s task_id=%s correlation_id=%s "
            "record_count=0 duration=0 final_status=cancelled",
            source_code,
            task_id,
            correlation_id,
        )
        return {
            "records_received": 0,
            "records_created": 0,
            "records_updated": 0,
            "records_skipped": 0,
            "records_failed": 0,
            "duplicate_candidates": 0,
            "status": SyncStatus.cancelled.value,
        }

    logger.info(
        "sync_started source_code=%s task_id=%s correlation_id=%s",
        source_code,
        task_id,
        correlation_id,
    )
    records = await _collector(source_code).collect_for_import()
    async with AsyncSessionFactory() as session:
        statistics = await import_opportunities(
            session,
            records,
            source_code=source_code,
            actor_id=triggered_by or "celery-beat",
            correlation_id=correlation_id,
            task_id=task_id,
        )

    final_status = (
        SyncStatus.partially_completed
        if statistics.records_failed
        else SyncStatus.completed
    )
    async with AsyncSessionFactory() as session:
        async with session.begin():
            history = await session.scalar(
                select(OpportunitySyncHistory).where(
                    OpportunitySyncHistory.task_id == task_id
                )
            )
            source = await session.scalar(
                select(OpportunitySource).where(
                    OpportunitySource.source_code == source_code
                )
            )
            history.finished_at = utc_now()
            history.records_received = statistics.records_received
            history.records_created = statistics.records_created
            history.records_updated = statistics.records_updated
            history.records_skipped = statistics.records_skipped
            history.records_failed = statistics.records_failed
            history.duplicate_candidates = statistics.duplicate_candidates
            history.status = final_status
            history.error_summary = (
                f"{statistics.records_failed} record(s) failed validation or import."
                if statistics.records_failed
                else None
            )
            if final_status == SyncStatus.completed:
                source.last_successful_sync_at = history.finished_at
                source.most_recent_error = None
            else:
                source.last_failed_sync_at = history.finished_at
                source.most_recent_error = history.error_summary
            source.next_scheduled_sync = history.finished_at + timedelta(
                hours=12 if source_code == "eu_funding_tenders" else 6
            )
            append_audit(
                session,
                actor_id=triggered_by,
                action=(
                    "scheduled_synchronization"
                    if not triggered_by
                    else "manual_synchronization"
                ),
                entity_type="opportunity_source",
                entity_id=source.id,
                new_value={
                    "task_id": task_id,
                    "status": final_status.value,
                    **statistics.model_dump(),
                },
                correlation_id=correlation_id,
            )

    duration = monotonic() - started
    logger.info(
        "sync_%s source_code=%s task_id=%s correlation_id=%s "
        "record_count=%s duration=%.3f final_status=%s",
        final_status.value,
        source_code,
        task_id,
        correlation_id,
        statistics.records_received,
        duration,
        final_status.value,
    )
    return {**statistics.model_dump(), "status": final_status.value}


async def _mark_retry(task_id: str, source_code: str, error: Exception) -> None:
    async with AsyncSessionFactory() as session:
        async with session.begin():
            history = await session.scalar(
                select(OpportunitySyncHistory).where(
                    OpportunitySyncHistory.task_id == task_id
                )
            )
            if history:
                history.status = SyncStatus.queued
                history.error_summary = _safe_error(error)


async def _mark_failed(task_id: str, source_code: str, error: Exception) -> None:
    now = utc_now()
    summary = _safe_error(error)
    correlation_id = "unknown"
    duration = 0.0
    async with AsyncSessionFactory() as session:
        async with session.begin():
            history = await session.scalar(
                select(OpportunitySyncHistory).where(
                    OpportunitySyncHistory.task_id == task_id
                )
            )
            source = await session.scalar(
                select(OpportunitySource).where(
                    OpportunitySource.source_code == source_code
                )
            )
            if history:
                history.status = SyncStatus.failed
                history.finished_at = now
                history.error_summary = summary
                correlation_id = history.correlation_id
                started_at = history.started_at
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=UTC)
                duration = max((now - started_at).total_seconds(), 0.0)
            if source:
                source.last_failed_sync_at = now
                source.most_recent_error = summary
    logger.error(
        "sync_failed source_code=%s task_id=%s correlation_id=%s "
        "record_count=0 duration=%.3f final_status=failed",
        source_code,
        task_id,
        correlation_id,
        duration,
    )


def _collector(source_code: str) -> Any:
    return {
        "grants_gov": GrantsGovSource,
        "simpler_grants": SimplerGrantsSource,
        "eu_funding_tenders": EUFundingSource,
    }[source_code]()


def _safe_error(error: Exception) -> str:
    if isinstance(error, ExternalAPIError):
        return str(error)[:1000]
    return "Synchronization failed due to an internal error."


@celery_app.task(name="app.tasks.opportunity_sync.retry_failed_records")
def retry_failed_records() -> dict[str, int]:
    return run_async_safely(_retry_failed_records())


async def _retry_failed_records() -> dict[str, int]:
    retried = 0
    async with AsyncSessionFactory() as session:
        failed = (
            await session.scalars(
                select(RawExternalOpportunity).where(
                    RawExternalOpportunity.processing_status == ProcessingStatus.failed
                )
            )
        ).all()
        for raw in failed:
            source = await session.get(OpportunitySource, raw.source_id)
            try:
                normalized = _collector(source.source_code)._normalize(raw.raw_payload)
            except Exception:
                continue
            raw.payload_hash = ""
            await session.commit()
            await import_opportunities(
                session,
                [normalized],
                source_code=source.source_code,
                actor_id="failed-record-retry",
            )
            retried += 1
    return {"retried": retried}


@celery_app.task(name="app.tasks.opportunity_sync.detect_expired_opportunities")
def detect_expired_opportunities() -> dict[str, int]:
    return run_async_safely(_detect_expired_opportunities())


async def _detect_expired_opportunities() -> dict[str, int]:
    changed = 0
    today = utc_now().date()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            opportunities = (
                await session.scalars(
                    select(ExternalOpportunity).where(
                        ExternalOpportunity.deadline < today,
                        ExternalOpportunity.verification_status
                        != VerificationStatus.expired,
                    )
                )
            ).all()
            for opportunity in opportunities:
                previous = opportunity.verification_status.value
                opportunity.verification_status = VerificationStatus.expired
                opportunity.publication_status = PublicationStatus.archived
                session.add(
                    VerificationHistory(
                        opportunity_id=opportunity.id,
                        previous_status=previous,
                        new_status=VerificationStatus.expired.value,
                        reason="Opportunity deadline has passed.",
                    )
                )
                changed += 1
    return {"expired": changed}


@celery_app.task(name="app.tasks.opportunity_sync.schedule_reverification")
def schedule_reverification() -> dict[str, int]:
    return run_async_safely(_schedule_reverification())


async def _schedule_reverification() -> dict[str, int]:
    scheduled = 0
    cutoff = utc_now() - timedelta(days=90)
    async with AsyncSessionFactory() as session:
        async with session.begin():
            reviews = (
                await session.scalars(
                    select(VerificationReview).where(
                        VerificationReview.verified_at.is_not(None),
                        VerificationReview.verified_at <= cutoff,
                    )
                )
            ).all()
            for review in reviews:
                opportunity = await session.get(ExternalOpportunity, review.opportunity_id)
                if opportunity.verification_status != VerificationStatus.verified:
                    continue
                opportunity.verification_status = VerificationStatus.reverification_required
                review.decision = VerificationStatus.reverification_required.value
                session.add(
                    VerificationHistory(
                        opportunity_id=opportunity.id,
                        previous_status=VerificationStatus.verified.value,
                        new_status=VerificationStatus.reverification_required.value,
                        reason="Scheduled 90-day reverification is due.",
                    )
                )
                scheduled += 1
    return {"scheduled": scheduled}


@celery_app.task(name="app.tasks.opportunity_sync.send_reverification_reminders")
def send_reverification_reminders() -> dict[str, int]:
    return run_async_safely(_send_reverification_reminders())


async def _send_reverification_reminders() -> dict[str, int]:
    async with AsyncSessionFactory() as session:
        reminders = len(
            (
                await session.scalars(
                    select(ExternalOpportunity.id).where(
                        ExternalOpportunity.verification_status
                        == VerificationStatus.reverification_required
                    )
                )
            ).all()
        )
    logger.info("reverification_reminders record_count=%s", reminders)
    return {"reminders": reminders}
