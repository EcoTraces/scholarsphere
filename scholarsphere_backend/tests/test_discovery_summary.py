from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import ExternalOpportunity, VerificationHistory
from app.models.external_opportunity import PublicationStatus, VerificationStatus
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.opportunity_import import import_opportunities
from app.services.parsing import utc_now
from app.services.source_registry import seed_opportunity_sources

ENDPOINT = "/api/v1/external-opportunities/discovery-summary"


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


async def _seed_opportunity(
    session: AsyncSession,
    *,
    external_id: str,
    country: str | None = "United States",
    verification_status: VerificationStatus = VerificationStatus.pending,
    publication_status: PublicationStatus = PublicationStatus.unpublished,
    link_checked_at=None,
    duplicate_review_required: bool = False,
    link_health_demoted: bool = False,
) -> str:
    record = NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id=external_id,
        title="Community Resilience Grant",
        opportunity_type="grant",
        provider_name="Department of Resilience",
        country=country,
        deadline=date.today() + timedelta(days=30),
        opportunity_status="posted",
        official_source_url=f"https://example.test/{external_id}",
        official_application_url=f"https://example.test/{external_id}/apply",
        raw_payload={"id": external_id},
    )
    await import_opportunities(session, [record], source_code="grants_gov", actor_id="officer-1")
    async with session.begin():
        opportunity = await session.scalar(
            select(ExternalOpportunity).where(ExternalOpportunity.external_id == external_id)
        )
        opportunity.verification_status = verification_status
        opportunity.publication_status = publication_status
        opportunity.link_checked_at = link_checked_at
        opportunity.duplicate_review_required = duplicate_review_required
        if link_health_demoted:
            session.add(
                VerificationHistory(
                    opportunity_id=opportunity.id,
                    previous_status=VerificationStatus.verified.value,
                    new_status=VerificationStatus.reverification_required.value,
                    reason="Routine link health check could not reach the stored "
                    "application/source URL.",
                )
            )
        opportunity_id = str(opportunity.id)
    return opportunity_id


@pytest.mark.asyncio
async def test_discovery_summary_reports_source_and_opportunity_totals(
    session: AsyncSession,
) -> None:
    await _seed_opportunity(session, external_id="disc-1", country="Kenya")
    await _seed_opportunity(session, external_id="disc-2", country="Kenya")
    await _seed_opportunity(session, external_id="disc-3", country="Germany")
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(ENDPOINT)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["opportunities_total"] == 3
    assert body["opportunities_by_country"]["Kenya"] == 2
    assert body["opportunities_by_country"]["Germany"] == 1
    assert body["sources_total"] > 0
    assert body["sources_active"] == body["sources_total"]
    assert body["sources_with_recent_errors"] == 0


@pytest.mark.asyncio
async def test_discovery_summary_counts_duplicate_review_and_published(
    session: AsyncSession,
) -> None:
    await _seed_opportunity(
        session,
        external_id="disc-dup",
        duplicate_review_required=True,
    )
    await _seed_opportunity(
        session,
        external_id="disc-published",
        verification_status=VerificationStatus.verified,
        publication_status=PublicationStatus.published,
        link_checked_at=utc_now(),
    )
    overrides(session, "administrator")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(ENDPOINT)
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert body["duplicate_review_required"] == 1
    assert body["published_total"] == 1
    assert body["never_link_checked"] == 0


@pytest.mark.asyncio
async def test_discovery_summary_counts_never_checked_and_broken_links(
    session: AsyncSession,
) -> None:
    await _seed_opportunity(
        session,
        external_id="disc-never-checked",
        verification_status=VerificationStatus.verified,
        publication_status=PublicationStatus.published,
        link_checked_at=None,
    )
    await _seed_opportunity(
        session,
        external_id="disc-broken",
        verification_status=VerificationStatus.reverification_required,
        publication_status=PublicationStatus.published,
        link_checked_at=utc_now(),
        link_health_demoted=True,
    )
    # Demoted by the 90-day schedule, not a broken link - must not be
    # counted as broken.
    await _seed_opportunity(
        session,
        external_id="disc-scheduled-reverify",
        verification_status=VerificationStatus.reverification_required,
        publication_status=PublicationStatus.published,
        link_checked_at=utc_now(),
        link_health_demoted=False,
    )
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(ENDPOINT)
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert body["never_link_checked"] == 1
    assert body["broken_links"] == 1


@pytest.mark.asyncio
async def test_discovery_summary_denied_for_applicant(session: AsyncSession) -> None:
    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(ENDPOINT)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
