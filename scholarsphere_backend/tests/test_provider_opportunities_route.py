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


def _registration_payload(*, uid: str, domain: str = "education.example") -> dict:
    return {
        "organization_name": "Global Education Foundation",
        "organization_type": "Foundation",
        "registration_number": "GEF-2026-001",
        "country": "Global",
        "official_website": f"https://{domain}",
        "official_email_domain": domain,
        "physical_address": "International Programs Office",
        "contact_person": "Provider Administrator",
        "contact_phone": "+000000000",
        "supporting_documents": [f"provider-documents/{uid}/registration-certificate.pdf"],
        "social_media_links": [],
    }


async def _register_and_verify(client: AsyncClient, session: AsyncSession, *, uid: str, domain: str) -> str:
    overrides(session, "applicant", uid=uid)
    response = await client.post(
        "/api/v1/providers", json=_registration_payload(uid=uid, domain=domain)
    )
    assert response.status_code == 200, response.text
    provider_id = response.json()["id"]

    overrides(session, "verificationOfficer")
    review = await client.post(
        f"/api/v1/providers/{provider_id}/review",
        json={
            "decision": "verified",
            "official_email_verified": True,
            "domain_verified": True,
            "contact_verified": True,
            "documents_verified": True,
            "impersonation_check_passed": True,
        },
    )
    assert review.status_code == 200, review.text
    return provider_id


def _submission_payload(*, provider_id: str) -> dict:
    return {
        "provider_id": provider_id,
        "title": "Global Leadership Scholarship",
        "host_institution": "Global Education Foundation",
        "host_country": "Global",
        "opportunity_type": "scholarship",
        "funding_type": "fullyFunded",
        "delivery_format": "hybrid",
        "deadline": (date.today() + timedelta(days=60)).isoformat(),
        "application_open_date": date.today().isoformat(),
        "official_source_url": "https://education.example/scholarship",
        "application_url": "https://education.example/scholarship/apply",
        "eligible_nationalities": ["Any"],
        "study_levels": ["Undergraduate"],
        "fields_of_study": ["Any"],
        "summary": "A fully-funded scholarship for outstanding students.",
        "benefits": ["Tuition", "Stipend"],
        "eligibility_requirements": ["GPA 3.5+"],
        "required_documents": ["Transcript"],
        "application_procedure": ["Submit online form"],
        "language_requirements": ["English"],
        "minimum_age": 18,
        "maximum_age": None,
        "work_experience_years_required": None,
        "contact_information": "admissions@education.example",
        "available_positions": 5,
        "application_fee": 0,
    }


@pytest.mark.asyncio
async def test_submission_requires_verified_provider_with_publish_permission(
    session: AsyncSession,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="owner-a")
        registered = await client.post(
            "/api/v1/providers",
            json=_registration_payload(uid="owner-a", domain="pending.example"),
        )
        provider_id = registered.json()["id"]

        response = await client.post(
            "/api/v1/provider-opportunities", json=_submission_payload(provider_id=provider_id)
        )
    app.dependency_overrides.clear()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_submission_with_unrelated_provider_id_is_403(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        provider_id = await _register_and_verify(
            client, session, uid="owner-b", domain="verified-b.example"
        )

        overrides(session, "applicant", uid="stranger")
        response = await client.post(
            "/api/v1/provider-opportunities", json=_submission_payload(provider_id=provider_id)
        )
    app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_submission_by_registered_administrator_succeeds(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        provider_id = await _register_and_verify(
            client, session, uid="owner-c", domain="verified-c.example"
        )

        overrides(session, "applicant", uid="owner-c")
        await client.post(
            f"/api/v1/providers/{provider_id}/administrators",
            json={"user_id": "admin-c", "email": "admin-c@example.test", "permissions": []},
        )

        overrides(session, "applicant", uid="admin-c")
        response = await client.post(
            "/api/v1/provider-opportunities", json=_submission_payload(provider_id=provider_id)
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["submitted_by"] == "admin-c"
    assert body["verification_status"] == "pending"
    assert body["opportunity_type"] == "scholarship"
    assert body["funding_type"] == "fullyFunded"


@pytest.mark.asyncio
async def test_verification_with_incomplete_checklist_is_409(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        provider_id = await _register_and_verify(
            client, session, uid="owner-d", domain="verified-d.example"
        )
        overrides(session, "applicant", uid="owner-d")
        submitted = await client.post(
            "/api/v1/provider-opportunities", json=_submission_payload(provider_id=provider_id)
        )
        opportunity_id = submitted.json()["id"]

        overrides(session, "verificationOfficer")
        response = await client.post(
            f"/api/v1/provider-opportunities/{opportunity_id}/verification",
            json={
                "decision": "approved",
                "source_checked": True,
                "application_link_checked": True,
                "deadline_checked": False,
                "duplicate_checked": True,
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_verify_then_publish_is_visible_but_not_via_public_opportunities(
    session: AsyncSession,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        provider_id = await _register_and_verify(
            client, session, uid="owner-e", domain="verified-e.example"
        )
        overrides(session, "applicant", uid="owner-e")
        submitted = await client.post(
            "/api/v1/provider-opportunities", json=_submission_payload(provider_id=provider_id)
        )
        opportunity_id = submitted.json()["id"]

        overrides(session, "verificationOfficer")
        verify = await client.post(
            f"/api/v1/provider-opportunities/{opportunity_id}/verification",
            json={
                "decision": "approved",
                "source_checked": True,
                "application_link_checked": True,
                "deadline_checked": True,
                "duplicate_checked": True,
            },
        )
        assert verify.status_code == 200, verify.text

        overrides(session, "administrator")
        publish = await client.post(
            f"/api/v1/provider-opportunities/{opportunity_id}/publication",
            json={"published": True},
        )
        assert publish.status_code == 200, publish.text

        admin_listing = await client.get("/api/v1/provider-opportunities/admin")

        overrides(session, "applicant", uid="owner-e")
        mine = await client.get(f"/api/v1/provider-opportunities/mine/{provider_id}")

        overrides(session, "applicant", uid="someone-else")
        public_listing = await client.get("/api/v1/opportunities")
    app.dependency_overrides.clear()

    assert admin_listing.json()["total"] == 1
    assert admin_listing.json()["items"][0]["publication_status"] == "published"
    assert len(mine.json()) == 1
    assert mine.json()[0]["verification_status"] == "verified"
    # Provider-submitted opportunities must never leak into the Grants.gov-
    # family public listing - the two pipelines are deliberately isolated.
    assert public_listing.json()["total"] == 0


@pytest.mark.asyncio
async def test_publish_before_verify_is_409(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        provider_id = await _register_and_verify(
            client, session, uid="owner-f", domain="verified-f.example"
        )
        overrides(session, "applicant", uid="owner-f")
        submitted = await client.post(
            "/api/v1/provider-opportunities", json=_submission_payload(provider_id=provider_id)
        )
        opportunity_id = submitted.json()["id"]

        overrides(session, "administrator")
        response = await client.post(
            f"/api/v1/provider-opportunities/{opportunity_id}/publication",
            json={"published": True},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_cross_provider_admin_cannot_manage_other_providers_opportunity(
    session: AsyncSession,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        provider_a = await _register_and_verify(
            client, session, uid="owner-g", domain="verified-g.example"
        )
        await _register_and_verify(client, session, uid="owner-h", domain="verified-h.example")

        overrides(session, "applicant", uid="owner-g")
        submitted = await client.post(
            "/api/v1/provider-opportunities", json=_submission_payload(provider_id=provider_a)
        )
        opportunity_id = submitted.json()["id"]

        overrides(session, "applicant", uid="owner-h")
        response = await client.get(f"/api/v1/provider-opportunities/mine/{provider_a}")
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert opportunity_id  # sanity: submission succeeded before the cross-provider check


@pytest.mark.asyncio
async def test_admin_listing_requires_staff_role(session: AsyncSession) -> None:
    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/provider-opportunities/admin")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
