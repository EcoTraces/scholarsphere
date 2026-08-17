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


async def _import_one(
    session: AsyncSession, *, deadline: date, external_id: str = "app-grant-1"
) -> str:
    record = NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id=external_id,
        title="Education Innovation Grant",
        opportunity_type="grant",
        provider_name="Department of Education",
        country="United States",
        deadline=deadline,
        opportunity_status="posted",
        official_source_url=f"https://example.test/{external_id}",
        official_application_url=f"https://example.test/{external_id}/apply",
        raw_payload={
            "id": external_id,
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
    opportunity = await session.scalar(
        select(ExternalOpportunity).where(ExternalOpportunity.external_id == external_id)
    )
    opportunity_id = str(opportunity.id)
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


async def _publish_opportunity(session: AsyncSession, *, deadline: date, external_id: str) -> str:
    opportunity_id = await _import_one(session, deadline=deadline, external_id=external_id)
    overrides(session, "administrator")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await _verify_and_publish(client, opportunity_id)
    finally:
        app.dependency_overrides.clear()
    return opportunity_id


@pytest.mark.asyncio
async def test_save_opportunity_creates_application(session: AsyncSession) -> None:
    deadline = date.today() + timedelta(days=10)
    opportunity_id = await _publish_opportunity(session, deadline=deadline, external_id="save-1")

    overrides(session, "applicant", uid="applicant-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/applications", json={"opportunity_id": opportunity_id}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["opportunity_title"] == "Education Innovation Grant"
    assert body["provider_name"] == "Department of Education"
    assert body["stage"] == "saved"
    assert body["deadline"] == deadline.isoformat()


@pytest.mark.asyncio
async def test_save_is_idempotent(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=5), external_id="save-2"
    )

    overrides(session, "applicant", uid="applicant-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await client.post(
                "/api/v1/applications", json={"opportunity_id": opportunity_id}
            )
            second = await client.post(
                "/api/v1/applications", json={"opportunity_id": opportunity_id}
            )
            listing = await client.get("/api/v1/applications")
    finally:
        app.dependency_overrides.clear()

    assert first.json()["id"] == second.json()["id"]
    assert len(listing.json()) == 1


@pytest.mark.asyncio
async def test_save_unpublished_opportunity_is_rejected(session: AsyncSession) -> None:
    opportunity_id = await _import_one(
        session, deadline=date.today() + timedelta(days=5), external_id="save-3"
    )

    overrides(session, "applicant", uid="applicant-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/applications", json={"opportunity_id": opportunity_id}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_save_nonexistent_opportunity_is_rejected(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="applicant-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/applications",
                json={"opportunity_id": "00000000-0000-4000-8000-000000000000"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_for_user_returns_only_own_records(session: AsyncSession) -> None:
    opportunity_a = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=5), external_id="save-4a"
    )
    opportunity_b = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=6), external_id="save-4b"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="applicant-a")
        await client.post("/api/v1/applications", json={"opportunity_id": opportunity_a})
        overrides(session, "applicant", uid="applicant-b")
        await client.post("/api/v1/applications", json={"opportunity_id": opportunity_b})

        overrides(session, "applicant", uid="applicant-a")
        listing = await client.get("/api/v1/applications")
    app.dependency_overrides.clear()

    body = listing.json()
    assert len(body) == 1
    assert body[0]["opportunity_id"] == opportunity_a


@pytest.mark.asyncio
async def test_get_by_opportunity_own_record(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=5), external_id="save-5"
    )

    overrides(session, "applicant", uid="applicant-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post("/api/v1/applications", json={"opportunity_id": opportunity_id})
            response = await client.get(f"/api/v1/applications/by-opportunity/{opportunity_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["opportunity_id"] == opportunity_id


@pytest.mark.asyncio
async def test_get_by_opportunity_not_saved_is_404(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=5), external_id="save-6"
    )

    overrides(session, "applicant", uid="applicant-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/api/v1/applications/by-opportunity/{opportunity_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_by_opportunity_saved_by_other_user_is_404(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=5), external_id="save-7"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="applicant-a")
        await client.post("/api/v1/applications", json={"opportunity_id": opportunity_id})

        overrides(session, "applicant", uid="applicant-b")
        response = await client.get(f"/api/v1/applications/by-opportunity/{opportunity_id}")
    app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cross_user_patch_is_404(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=5), external_id="save-8"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="applicant-a")
        created = await client.post(
            "/api/v1/applications", json={"opportunity_id": opportunity_id}
        )
        application_id = created.json()["id"]

        overrides(session, "applicant", uid="applicant-b")
        patch = await client.patch(
            f"/api/v1/applications/{application_id}",
            json={"stage": "applicationSubmitted", "personal_notes": "hijacked"},
        )

        overrides(session, "applicant", uid="applicant-a")
        unchanged = await client.get(f"/api/v1/applications/by-opportunity/{opportunity_id}")
    app.dependency_overrides.clear()

    assert patch.status_code == 404
    assert unchanged.json()["stage"] == "saved"
    assert unchanged.json()["personal_notes"] == ""


@pytest.mark.asyncio
async def test_patch_full_replace_updates_all_fields(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=5), external_id="save-9"
    )

    overrides(session, "applicant", uid="applicant-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            created = await client.post(
                "/api/v1/applications", json={"opportunity_id": opportunity_id}
            )
            application_id = created.json()["id"]
            patch = await client.patch(
                f"/api/v1/applications/{application_id}",
                json={
                    "stage": "applicationSubmitted",
                    "application_date": "2026-08-01",
                    "application_reference_number": "REF-123",
                    "missing_documents": ["transcript"],
                    "interview_date": "2026-08-15",
                    "personal_notes": "Submitted early.",
                    "result_date": None,
                    "scholarship_value": 5000.0,
                    "follow_up_actions": ["send thank-you email"],
                },
            )
            fetched = await client.get(f"/api/v1/applications/by-opportunity/{opportunity_id}")
    finally:
        app.dependency_overrides.clear()

    assert patch.status_code == 200
    for body in (patch.json(), fetched.json()):
        assert body["stage"] == "applicationSubmitted"
        assert body["application_date"] == "2026-08-01"
        assert body["application_reference_number"] == "REF-123"
        assert body["missing_documents"] == ["transcript"]
        assert body["interview_date"] == "2026-08-15"
        assert body["personal_notes"] == "Submitted early."
        assert body["result_date"] is None
        assert body["scholarship_value"] == 5000.0
        assert body["follow_up_actions"] == ["send thank-you email"]


@pytest.mark.asyncio
async def test_patch_nonexistent_id_is_404(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="applicant-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                "/api/v1/applications/00000000-0000-4000-8000-000000000000",
                json={"stage": "saved"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_listing_requires_staff_role(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="applicant-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/applications/admin")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_listing_returns_all_users_paginated(session: AsyncSession) -> None:
    opportunity_a = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=5), external_id="save-10a"
    )
    opportunity_b = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=6), external_id="save-10b"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="applicant-a")
        await client.post("/api/v1/applications", json={"opportunity_id": opportunity_a})
        overrides(session, "applicant", uid="applicant-b")
        await client.post("/api/v1/applications", json={"opportunity_id": opportunity_b})

        overrides(session, "administrator")
        full = await client.get("/api/v1/applications/admin")
        paged = await client.get("/api/v1/applications/admin", params={"page_size": 1})
    app.dependency_overrides.clear()

    assert full.json()["total"] == 2
    assert len(full.json()["items"]) == 2
    assert paged.json()["total"] == 2
    assert len(paged.json()["items"]) == 1


@pytest.mark.asyncio
async def test_applications_require_authentication(session: AsyncSession) -> None:
    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = database
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/applications")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
