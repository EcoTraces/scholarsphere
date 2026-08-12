from collections.abc import AsyncIterator
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models import (
    ExternalOpportunity,
    ImportAuditLog,
    OpportunitySource,
    RawExternalOpportunity,
    VerificationHistory,
    VerificationReview,
)
from app.models.external_opportunity import (
    ProcessingStatus,
    PublicationStatus,
    VerificationStatus,
)
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.opportunity_import import import_opportunities
from app.services.parsing import duplicate_fingerprint, payload_hash
from app.services.source_registry import seed_opportunity_sources


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


def normalized(
    *,
    source_code: str = "grants_gov",
    external_id: str = "grant-1",
    title: str = "Education Innovation Grant",
    provider: str = "Department of Education",
    deadline: date = date(2026, 9, 30),
    status: str = "posted",
    payload_version: int = 1,
) -> NormalizedExternalOpportunity:
    return NormalizedExternalOpportunity(
        source_code=source_code,
        external_id=external_id,
        external_reference=f"REF-{external_id}",
        title=title,
        opportunity_type="grant",
        provider_name=provider,
        provider_code="ED",
        country="United States",
        deadline=deadline,
        opportunity_status=status,
        award_floor=1000,
        award_ceiling=50000,
        currency="USD",
        official_source_url=f"https://example.test/{external_id}",
        official_application_url=f"https://example.test/{external_id}/apply",
        raw_payload={"id": external_id, "version": payload_version},
    )


@pytest.mark.asyncio
async def test_source_seeding_is_idempotent(session: AsyncSession) -> None:
    async with session.begin():
        first = await seed_opportunity_sources(session)
    async with session.begin():
        second = await seed_opportunity_sources(session)

    assert set(first) == {
        "grants_gov",
        "simpler_grants",
        "eu_funding_tenders",
        "usajobs",
        "reliefweb_jobs",
        "reliefweb_training",
    }
    assert first["grants_gov"].id == second["grants_gov"].id
    assert await session.scalar(select(func.count(OpportunitySource.id))) == 6


@pytest.mark.asyncio
async def test_import_stores_raw_hash_opportunity_queue_and_audit(
    session: AsyncSession,
) -> None:
    item = normalized()
    statistics = await import_opportunities(
        session, [item], source_code="grants_gov", actor_id="officer-1"
    )

    raw = await session.scalar(select(RawExternalOpportunity))
    opportunity = await session.scalar(select(ExternalOpportunity))
    review = await session.scalar(select(VerificationReview))
    audit = await session.scalar(select(ImportAuditLog))
    assert statistics.model_dump() == {
        "records_received": 1,
        "records_created": 1,
        "records_updated": 0,
        "records_skipped": 0,
        "records_failed": 0,
        "duplicate_candidates": 0,
    }
    assert raw is not None and raw.raw_payload == item.raw_payload
    assert raw.payload_hash == payload_hash(item.raw_payload)
    assert raw.processing_status == ProcessingStatus.imported
    assert raw.opportunity_id == opportunity.id
    assert opportunity.verification_status == VerificationStatus.pending
    assert opportunity.publication_status == PublicationStatus.unpublished
    assert review is not None and review.decision == "pending"
    assert audit is not None and audit.action == "external_import_created"


@pytest.mark.asyncio
async def test_exact_duplicate_is_skipped(session: AsyncSession) -> None:
    item = normalized()
    await import_opportunities(
        session, [item], source_code="grants_gov", actor_id="officer-1"
    )
    statistics = await import_opportunities(
        session, [item], source_code="grants_gov", actor_id="officer-1"
    )

    assert statistics.records_skipped == 1
    assert await session.scalar(select(func.count(ExternalOpportunity.id))) == 1
    assert await session.scalar(select(func.count(RawExternalOpportunity.id))) == 1


@pytest.mark.asyncio
async def test_changed_payload_updates_raw_and_normalized_opportunity(
    session: AsyncSession,
) -> None:
    await import_opportunities(
        session, [normalized()], source_code="grants_gov", actor_id="officer-1"
    )
    changed = normalized(title="Updated title", payload_version=2)
    statistics = await import_opportunities(
        session, [changed], source_code="grants_gov", actor_id="officer-1"
    )

    raw = await session.scalar(select(RawExternalOpportunity))
    opportunity = await session.scalar(select(ExternalOpportunity))
    assert statistics.records_updated == 1
    assert raw.raw_payload == changed.raw_payload
    assert raw.payload_hash == payload_hash(changed.raw_payload)
    assert opportunity.title == "Updated title"
    assert opportunity.payload_hash == raw.payload_hash


@pytest.mark.asyncio
async def test_cross_source_duplicate_is_flagged_without_merging(
    session: AsyncSession,
) -> None:
    first = normalized()
    second = normalized(source_code="simpler_grants", external_id="simpler-1")
    await import_opportunities(
        session, [first], source_code="grants_gov", actor_id="officer-1"
    )
    statistics = await import_opportunities(
        session, [second], source_code="simpler_grants", actor_id="officer-1"
    )

    opportunities = (await session.scalars(select(ExternalOpportunity))).all()
    assert statistics.duplicate_candidates == 1
    assert len(opportunities) == 2
    assert all(item.duplicate_review_required for item in opportunities)
    assert opportunities[0].external_fingerprint == duplicate_fingerprint(
        first.title, first.provider_name, first.deadline
    )


@pytest.mark.asyncio
async def test_material_change_triggers_reverification_and_preserves_history(
    session: AsyncSession,
) -> None:
    await import_opportunities(
        session, [normalized()], source_code="grants_gov", actor_id="officer-1"
    )
    opportunity = await session.scalar(select(ExternalOpportunity))
    opportunity.verification_status = VerificationStatus.verified
    session.add(
        VerificationHistory(
            opportunity_id=opportunity.id,
            previous_status="pending",
            new_status="verified",
            reason="Initial review completed.",
        )
    )
    await session.commit()

    await import_opportunities(
        session,
        [normalized(deadline=date(2026, 10, 31), payload_version=2)],
        source_code="grants_gov",
        actor_id="officer-1",
    )

    await session.refresh(opportunity)
    history = (
        await session.scalars(
            select(VerificationHistory).order_by(VerificationHistory.changed_at)
        )
    ).all()
    assert opportunity.verification_status == VerificationStatus.reverification_required
    assert len(history) == 2
    assert history[-1].previous_status == "verified"
    assert history[-1].new_status == "reverification_required"
    assert "deadline" in history[-1].changed_fields


@pytest.mark.asyncio
async def test_invalid_item_does_not_fail_batch_and_records_error(
    session: AsyncSession,
) -> None:
    invalid = normalized(external_id="bad").model_dump()
    invalid["title"] = ""
    statistics = await import_opportunities(
        session,
        [invalid, normalized(external_id="good")],
        source_code="grants_gov",
        actor_id="officer-1",
    )

    failed_raw = await session.scalar(
        select(RawExternalOpportunity).where(
            RawExternalOpportunity.external_id == "bad"
        )
    )
    assert statistics.records_received == 2
    assert statistics.records_created == 1
    assert statistics.records_failed == 1
    assert failed_raw.processing_status == ProcessingStatus.failed
    assert failed_raw.processing_error


@pytest.mark.asyncio
async def test_outer_transaction_rolls_back_on_batch_failure(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import opportunity_import

    async def fail_seed(_: AsyncSession):
        raise RuntimeError("database failure")

    monkeypatch.setattr(opportunity_import, "seed_opportunity_sources", fail_seed)
    with pytest.raises(RuntimeError, match="database failure"):
        await import_opportunities(
            session,
            [normalized()],
            source_code="grants_gov",
            actor_id="officer-1",
        )
    assert await session.scalar(select(func.count(OpportunitySource.id))) == 0
