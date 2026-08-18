from collections.abc import AsyncIterator

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


def _registration_payload(*, uid: str, **overrides_kwargs: object) -> dict:
    payload = {
        "organization_name": "Global Education Foundation",
        "organization_type": "Foundation",
        "registration_number": "GEF-2026-001",
        "country": "Global",
        "official_website": "https://education.example",
        "official_email_domain": "education.example",
        "physical_address": "International Programs Office",
        "contact_person": "Provider Administrator",
        "contact_phone": "+000000000",
        "supporting_documents": [f"provider-documents/{uid}/registration-certificate.pdf"],
        "social_media_links": [],
    }
    payload.update(overrides_kwargs)
    return payload


async def _register(client: AsyncClient, *, uid: str, **overrides_kwargs: object) -> dict:
    response = await client.post(
        "/api/v1/providers", json=_registration_payload(uid=uid, **overrides_kwargs)
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_registration_creates_pending_review_with_server_risk_score(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="provider-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            body = await _register(client, uid="provider-a")
    finally:
        app.dependency_overrides.clear()

    assert body["status"] == "pendingReview"
    assert body["risk_score"] == 0
    assert body["permissions"] == ["manageOrganization"]


@pytest.mark.asyncio
async def test_registration_computes_risk_score_server_side_and_ignores_client_value(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="provider-b")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            payload = _registration_payload(
                uid="provider-b",
                official_email_domain="gmail.com",
                registration_number="",
                supporting_documents=[],
                risk_score=999,
            )
            response = await client.post("/api/v1/providers", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    # gmail.com (+55) + website doesn't match domain (+25) + empty registration
    # number (+15) + no documents (+15) = 110, clamped to 100
    assert body["risk_score"] == 100


@pytest.mark.asyncio
async def test_registration_document_outside_own_uid_folder_is_rejected(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="provider-c")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            payload = _registration_payload(
                uid="provider-c",
                supporting_documents=["provider-documents/someone-else/doc.pdf"],
            )
            response = await client.post("/api/v1/providers", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_domain_rejected_case_insensitively(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="provider-d1")
        await _register(client, uid="provider-d1", official_email_domain="Education.Example")

        overrides(session, "applicant", uid="provider-d2")
        response = await client.post(
            "/api/v1/providers",
            json=_registration_payload(
                uid="provider-d2",
                official_email_domain="EDUCATION.EXAMPLE",
            ),
        )
    app.dependency_overrides.clear()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_review_with_incomplete_checklist_and_verified_decision_is_409(
    session: AsyncSession,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="provider-e")
        provider = await _register(client, uid="provider-e")

        overrides(session, "verificationOfficer")
        response = await client.post(
            f"/api/v1/providers/{provider['id']}/review",
            json={
                "decision": "verified",
                "official_email_verified": True,
                "domain_verified": True,
                "contact_verified": True,
                "documents_verified": False,
                "impersonation_check_passed": True,
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_review_with_complete_checklist_verifies_provider(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="provider-f")
        provider = await _register(client, uid="provider-f")

        overrides(session, "verificationOfficer", uid="officer-1")
        response = await client.post(
            f"/api/v1/providers/{provider['id']}/review",
            json={
                "decision": "verified",
                "official_email_verified": True,
                "domain_verified": True,
                "contact_verified": True,
                "documents_verified": True,
                "impersonation_check_passed": True,
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "verified"
    assert set(body["permissions"]) == {
        "manageOrganization",
        "publishOpportunities",
        "manageAdmins",
    }
    assert body["verified_by"] == "officer-1"
    assert body["verification_date"] is not None
    assert body["reverification_date"] is not None


@pytest.mark.asyncio
async def test_suspend_clears_permissions(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="provider-g")
        provider = await _register(client, uid="provider-g")

        overrides(session, "administrator")
        response = await client.post(
            f"/api/v1/providers/{provider['id']}/suspend", json={"reason": "Policy violation."}
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "suspended"
    assert body["permissions"] == []


@pytest.mark.asyncio
async def test_appeal_only_allowed_from_rejected_or_suspended(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="provider-h")
        provider = await _register(client, uid="provider-h")

        # still pending_review - appeal should be rejected
        response = await client.post(
            f"/api/v1/providers/{provider['id']}/appeal",
            json={"reason": "Please reconsider."},
        )
        assert response.status_code == 409

        overrides(session, "administrator")
        await client.post(
            f"/api/v1/providers/{provider['id']}/suspend", json={"reason": "Policy violation."}
        )

        overrides(session, "applicant", uid="provider-h")
        appealed = await client.post(
            f"/api/v1/providers/{provider['id']}/appeal",
            json={"reason": "Please reconsider."},
        )
    app.dependency_overrides.clear()

    assert appealed.status_code == 200
    body = appealed.json()
    assert body["status"] == "pendingReview"
    assert body["appeals"][0]["reason"] == "Please reconsider."


@pytest.mark.asyncio
async def test_add_administrator_requires_verified_badge(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="provider-i")
        provider = await _register(client, uid="provider-i")

        response = await client.post(
            f"/api/v1/providers/{provider['id']}/administrators",
            json={"user_id": "admin-1", "email": "admin@example.test", "permissions": []},
        )
        assert response.status_code == 409

        overrides(session, "verificationOfficer")
        await client.post(
            f"/api/v1/providers/{provider['id']}/review",
            json={
                "decision": "verified",
                "official_email_verified": True,
                "domain_verified": True,
                "contact_verified": True,
                "documents_verified": True,
                "impersonation_check_passed": True,
            },
        )

        overrides(session, "applicant", uid="provider-i")
        added = await client.post(
            f"/api/v1/providers/{provider['id']}/administrators",
            json={"user_id": "admin-1", "email": "admin@example.test", "permissions": []},
        )
    app.dependency_overrides.clear()

    assert added.status_code == 200
    body = added.json()
    assert body["administrators"][0]["user_id"] == "admin-1"
    assert any(item["action"] == "Administrator added" for item in body["activity_history"])


@pytest.mark.asyncio
async def test_cross_user_appeal_and_add_administrator_are_404(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="provider-j")
        provider = await _register(client, uid="provider-j")

        overrides(session, "applicant", uid="someone-else")
        appeal_response = await client.post(
            f"/api/v1/providers/{provider['id']}/appeal", json={"reason": "not mine"}
        )
        admin_response = await client.post(
            f"/api/v1/providers/{provider['id']}/administrators",
            json={"user_id": "x", "email": "x@example.test", "permissions": []},
        )
    app.dependency_overrides.clear()

    assert appeal_response.status_code == 404
    assert admin_response.status_code == 404


@pytest.mark.asyncio
async def test_can_publish_reflects_verification_and_permission(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="provider-k")
        provider = await _register(client, uid="provider-k")
        still_pending = await client.get("/api/v1/providers/me/can-publish")
        # The GET above autobegins a read transaction on the shared session
        # that nothing commits; close it explicitly before the next call
        # opens its own `session.begin()`, same as `_import_one`'s pattern
        # in test_public_opportunities_route.py.
        await session.commit()

        overrides(session, "verificationOfficer")
        await client.post(
            f"/api/v1/providers/{provider['id']}/review",
            json={
                "decision": "verified",
                "official_email_verified": True,
                "domain_verified": True,
                "contact_verified": True,
                "documents_verified": True,
                "impersonation_check_passed": True,
            },
        )

        overrides(session, "applicant", uid="provider-k")
        verified = await client.get("/api/v1/providers/me/can-publish")

        overrides(session, "applicant", uid="never-registered")
        unregistered = await client.get("/api/v1/providers/me/can-publish")
    app.dependency_overrides.clear()

    assert still_pending.json() == {"can_publish": False}
    assert verified.json() == {"can_publish": True}
    assert unregistered.json() == {"can_publish": False}


@pytest.mark.asyncio
async def test_review_queue_requires_staff_role(session: AsyncSession) -> None:
    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/providers/review-queue")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_review_queue_lists_pending_providers(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="provider-l")
        await _register(client, uid="provider-l")

        overrides(session, "administrator")
        response = await client.get("/api/v1/providers/review-queue")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_providers_require_authentication(session: AsyncSession) -> None:
    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = database
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/providers/me")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
