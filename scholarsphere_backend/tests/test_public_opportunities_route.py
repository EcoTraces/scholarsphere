from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.opportunity_import import import_opportunities
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


async def _import_one(session: AsyncSession, *, deadline: date) -> str:
    record = NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id="evidence-grant-1",
        title="Education Innovation Grant",
        opportunity_type="grant",
        provider_name="Department of Education",
        country="United States",
        deadline=deadline,
        opportunity_status="posted",
        official_source_url="https://example.test/evidence-grant-1",
        official_application_url="https://example.test/evidence-grant-1/apply",
        raw_payload={
            "id": "evidence-grant-1",
            "title": "Education Innovation Grant",
            "agencyName": "Department of Education",
            "openDate": "07/01/2026",
            "closeDate": deadline.isoformat(),
            "oppStatus": "posted",
        },
    )
    statistics = await import_opportunities(
        session, [record], source_code="grants_gov", actor_id="officer-1"
    )
    assert statistics.records_created == 1
    from sqlalchemy import select

    from app.models import ExternalOpportunity

    opportunity = await session.scalar(
        select(ExternalOpportunity).where(
            ExternalOpportunity.external_id == "evidence-grant-1"
        )
    )
    opportunity_id = str(opportunity.id)
    # Close the transaction this read autobegan so later API calls sharing
    # this same session (a test convenience; production requests each get
    # their own fresh session) don't collide with their own session.begin().
    await session.commit()
    return opportunity_id


async def _verify_and_publish(client: AsyncClient, opportunity_id: str) -> None:
    verify = await client.post(
        f"/api/v1/external-opportunities/opportunities/{opportunity_id}/verification",
        json={
            "decision": "approved",
            "notes": "Official source confirmed.",
            "source_checked": True,
            "application_link_checked": True,
            "deadline_checked": True,
            "duplicate_checked": True,
        },
    )
    assert verify.status_code == 200
    publish = await client.post(
        f"/api/v1/external-opportunities/opportunities/{opportunity_id}/publication",
        json={"published": True},
    )
    assert publish.status_code == 200


@pytest.mark.asyncio
async def test_full_pipeline_reaches_public_endpoint_with_evidence(
    session: AsyncSession,
) -> None:
    """End-to-end: import -> verify -> publish -> public listing + evidence."""
    deadline = date.today() + timedelta(days=10)
    opportunity_id = await _import_one(session, deadline=deadline)

    overrides(session, "administrator")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Not yet verified: must not appear publicly.
            before = await client.get("/api/v1/opportunities")
            assert before.status_code == 200
            assert before.json()["total"] == 0
            await session.commit()

            await _verify_and_publish(client, opportunity_id)

            # Verification history is a staff-only endpoint, checked here
            # while still authorized, not from the applicant's session below.
            history = await client.get(
                "/api/v1/external-opportunities/opportunities/"
                f"{opportunity_id}/verification-history"
            )
            assert history.status_code == 200
            history_body = history.json()
            assert len(history_body["items"]) == 1
            assert history_body["items"][0]["new_status"] == "verified"
    finally:
        app.dependency_overrides.clear()

    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            listing = await client.get("/api/v1/opportunities")
            assert listing.status_code == 200
            body = listing.json()
            assert body["total"] == 1
            item = body["items"][0]
            assert item["title"] == "Education Innovation Grant"
            assert item["verification_status"] == "verified"
            assert item["days_remaining"] == 10
            assert item["deadline_priority"] == "IMPORTANT"
            assert item["source_name"] == "Grants.gov"

            detail = await client.get(f"/api/v1/opportunities/{opportunity_id}")
            assert detail.status_code == 200
            assert detail.json()["id"] == opportunity_id

            evidence = await client.get(
                f"/api/v1/opportunities/{opportunity_id}/evidence"
            )
            assert evidence.status_code == 200
            evidence_body = evidence.json()
            assert evidence_body["raw_payload"]["closeDate"] == deadline.isoformat()
            deadline_evidence = next(
                item
                for item in evidence_body["field_evidence"]
                if item["field"] == "deadline"
            )
            assert deadline_evidence["value"] == deadline.isoformat()
            assert deadline_evidence["confidence"] == "HIGH"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_unverified_opportunity_is_never_public(session: AsyncSession) -> None:
    await _import_one(session, deadline=date.today() + timedelta(days=5))
    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            listing = await client.get("/api/v1/opportunities")
            assert listing.json()["total"] == 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_expired_opportunity_is_still_listed_but_flagged_expired(
    session: AsyncSession,
) -> None:
    opportunity_id = await _import_one(
        session, deadline=date.today() - timedelta(days=3)
    )
    overrides(session, "administrator")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await _verify_and_publish(client, opportunity_id)
            listing = await client.get("/api/v1/opportunities")
    finally:
        app.dependency_overrides.clear()
    item = listing.json()["items"][0]
    assert item["deadline_priority"] == "EXPIRED"
    assert item["days_remaining"] == -3


@pytest.mark.asyncio
async def test_public_endpoints_require_authentication(session: AsyncSession) -> None:
    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = database
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/opportunities")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
