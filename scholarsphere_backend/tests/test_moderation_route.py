from collections.abc import AsyncIterator
from datetime import date, timedelta
from uuid import UUID

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
from app.models import ExternalOpportunity
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


def user(role: str, uid: str | None = None) -> AuthenticatedUser:
    return AuthenticatedUser(
        uid=uid or f"{role}-user",
        email=f"{uid or role}@example.test",
        email_verified=True,
        role=role,
        permissions=frozenset(),
    )


def overrides(session: AsyncSession, role: str, uid: str | None = None) -> None:
    async def current_user() -> AuthenticatedUser:
        return user(role, uid)

    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


async def _publish_opportunity(session: AsyncSession, *, external_id: str) -> str:
    record = NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id=external_id,
        title="Education Innovation Grant",
        opportunity_type="grant",
        provider_name="Department of Education",
        country="United States",
        deadline=date.today() + timedelta(days=10),
        opportunity_status="posted",
        official_source_url=f"https://example.test/{external_id}",
        official_application_url=f"https://example.test/{external_id}/apply",
        raw_payload={
            "id": external_id,
            "title": "Education Innovation Grant",
            "agencyName": "Department of Education",
            "openDate": "07/01/2026",
            "closeDate": (date.today() + timedelta(days=10)).isoformat(),
            "oppStatus": "posted",
        },
    )
    statistics = await import_opportunities(
        session, [record], source_code="grants_gov", actor_id="officer-1"
    )
    assert statistics.records_created == 1
    opportunity = await session.scalar(
        select(ExternalOpportunity).where(ExternalOpportunity.external_id == external_id)
    )
    opportunity_id = str(opportunity.id)
    await session.commit()

    overrides(session, "administrator")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
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
        await client.post(
            f"/api/v1/external-opportunities/opportunities/{opportunity_id}/publication",
            json={"published": True},
        )
    app.dependency_overrides.clear()
    return opportunity_id


async def _register_provider(session: AsyncSession, *, uid: str) -> str:
    overrides(session, "applicant", uid=uid)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/providers",
            json={
                "organization_name": "Global Education Foundation",
                "organization_type": "Foundation",
                "registration_number": "GEF-2026-001",
                "country": "Global",
                "official_website": "https://education.example",
                "official_email_domain": "education.example",
                "physical_address": "International Programs Office",
                "contact_person": "Provider Administrator",
                "contact_phone": "+000000000",
                "supporting_documents": [f"provider-documents/{uid}/cert.pdf"],
                "social_media_links": [],
            },
        )
    app.dependency_overrides.clear()
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _submit_payload(entity_type: str, entity_id: str, report_type: str = "scam") -> dict:
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "report_type": report_type,
        "description": "Something looks wrong.",
        "evidence": [],
    }


@pytest.mark.asyncio
async def test_submit_report_against_real_opportunity(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(session, external_id="mod-1")
    overrides(session, "applicant", uid="reporter-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/moderation-cases",
                json=_submit_payload("opportunity", opportunity_id),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "submitted"
    assert body["reporter_id"] == "reporter-a"
    assert body["history"] == []


@pytest.mark.asyncio
async def test_submit_report_against_nonexistent_opportunity_is_404(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="reporter-b")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/moderation-cases",
                json=_submit_payload(
                    "opportunity", "00000000-0000-4000-8000-000000000000"
                ),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_open_report_is_rejected(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(session, external_id="mod-2")
    overrides(session, "applicant", uid="reporter-c")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await client.post(
                "/api/v1/moderation-cases",
                json=_submit_payload("opportunity", opportunity_id),
            )
            second = await client.post(
                "/api/v1/moderation-cases",
                json=_submit_payload("opportunity", opportunity_id),
            )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_user_entity_type_report_skips_existence_check(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="reporter-d")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/moderation-cases",
                json=_submit_payload("user", "some-firebase-uid"),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_queue_requires_moderation_role(session: AsyncSession) -> None:
    overrides(session, "supportOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/moderation-cases/queue")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_transition_content_removed_archives_opportunity(
    session: AsyncSession,
) -> None:
    opportunity_id = await _publish_opportunity(session, external_id="mod-3")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="reporter-e")
        created = await client.post(
            "/api/v1/moderation-cases",
            json=_submit_payload("opportunity", opportunity_id),
        )
        case_id = created.json()["id"]

        overrides(session, "moderator", uid="mod-officer-1")
        transitioned = await client.post(
            f"/api/v1/moderation-cases/{case_id}/transition",
            json={
                "status": "contentRemoved",
                "notes": "Confirmed scam listing.",
                "hide_content": False,
            },
        )
    app.dependency_overrides.clear()

    assert transitioned.status_code == 200
    body = transitioned.json()
    assert body["status"] == "contentRemoved"
    assert body["assigned_moderator_id"] == "mod-officer-1"
    assert len(body["history"]) == 1
    assert body["history"][0]["actor_id"] == "mod-officer-1"

    opportunity = await session.get(ExternalOpportunity, UUID(opportunity_id))
    assert opportunity.verification_status.value == "archived"


@pytest.mark.asyncio
async def test_transition_provider_suspended_suspends_provider(
    session: AsyncSession,
) -> None:
    provider_id = await _register_provider(session, uid="provider-owner-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="reporter-f")
        created = await client.post(
            "/api/v1/moderation-cases",
            json=_submit_payload("provider", provider_id),
        )
        case_id = created.json()["id"]

        overrides(session, "administrator")
        transitioned = await client.post(
            f"/api/v1/moderation-cases/{case_id}/transition",
            json={
                "status": "providerSuspended",
                "notes": "Fraudulent registration.",
                "hide_content": False,
            },
        )
    app.dependency_overrides.clear()

    assert transitioned.status_code == 200

    from app.models.provider import Provider

    provider = await session.get(Provider, UUID(provider_id))
    assert provider.status.value == "suspended"
    assert provider.permissions == []


@pytest.mark.asyncio
async def test_appeal_only_allowed_on_closed_cases(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(session, external_id="mod-4")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="reporter-g")
        created = await client.post(
            "/api/v1/moderation-cases",
            json=_submit_payload("opportunity", opportunity_id),
        )
        case_id = created.json()["id"]

        still_open = await client.post(
            f"/api/v1/moderation-cases/{case_id}/appeal",
            json={"reason": "This is not accurate."},
        )

        overrides(session, "moderator", uid="mod-officer-2")
        await client.post(
            f"/api/v1/moderation-cases/{case_id}/transition",
            json={"status": "rejected", "notes": "No evidence.", "hide_content": False},
        )

        overrides(session, "applicant", uid="reporter-g")
        appealed = await client.post(
            f"/api/v1/moderation-cases/{case_id}/appeal",
            json={"reason": "This is not accurate."},
        )
    app.dependency_overrides.clear()

    assert still_open.status_code == 409
    assert appealed.status_code == 200
    assert appealed.json()["status"] == "escalated"


@pytest.mark.asyncio
async def test_issue_warning_rejected_for_opportunity_entity(
    session: AsyncSession,
) -> None:
    opportunity_id = await _publish_opportunity(session, external_id="mod-5")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="reporter-h")
        created = await client.post(
            "/api/v1/moderation-cases",
            json=_submit_payload("opportunity", opportunity_id),
        )
        case_id = created.json()["id"]

        overrides(session, "moderator")
        response = await client.post(
            f"/api/v1/moderation-cases/{case_id}/warning",
            json={"reason": "test"},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_issue_warning_for_provider_resolves_case_and_is_listed(
    session: AsyncSession,
) -> None:
    provider_id = await _register_provider(session, uid="provider-owner-2")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="reporter-i")
        created = await client.post(
            "/api/v1/moderation-cases",
            json=_submit_payload("provider", provider_id, report_type="misleadingContent"),
        )
        case_id = created.json()["id"]

        overrides(session, "moderator", uid="mod-officer-3")
        warned = await client.post(
            f"/api/v1/moderation-cases/{case_id}/warning",
            json={"reason": "Misleading claims in listing."},
        )
        case_after = await client.get("/api/v1/moderation-cases/queue")
        listed = await client.get(
            "/api/v1/moderation-warnings",
            params={"entity_type": "provider", "entity_id": provider_id},
        )
    app.dependency_overrides.clear()

    assert warned.status_code == 200
    assert warned.json()["reason"] == "Misleading claims in listing."
    # resolved -> no longer in the open queue
    assert all(item["id"] != case_id for item in case_after.json())
    assert len(listed.json()) == 1
    assert listed.json()[0]["case_id"] == case_id


@pytest.mark.asyncio
async def test_get_for_reporter_is_scoped(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(session, external_id="mod-6")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="reporter-j")
        await client.post(
            "/api/v1/moderation-cases",
            json=_submit_payload("opportunity", opportunity_id),
        )

        overrides(session, "applicant", uid="reporter-k")
        their_reports = await client.get("/api/v1/moderation-cases/mine")
    app.dependency_overrides.clear()

    assert their_reports.json() == []


@pytest.mark.asyncio
async def test_analytics_requires_moderation_role(session: AsyncSession) -> None:
    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/moderation-cases/analytics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_moderation_requires_authentication(session: AsyncSession) -> None:
    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = database
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/moderation-cases/mine")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
