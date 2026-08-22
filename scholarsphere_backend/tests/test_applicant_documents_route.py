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


async def _add(client: AsyncClient, *, uid: str, doc_type: str, file_name: str) -> dict:
    response = await client.post(
        "/api/v1/applicant-documents",
        json={
            "type": doc_type,
            "file_name": file_name,
            "storage_path": f"applicant-documents/{uid}/{file_name}",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_list_before_add_is_empty(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="doc-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/applicant-documents/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_add_document_outside_own_uid_folder_is_rejected(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="doc-b")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/applicant-documents",
                json={
                    "type": "passport",
                    "file_name": "passport.pdf",
                    "storage_path": "applicant-documents/someone-else/passport.pdf",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_replaces_existing_document_of_same_type(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="doc-c")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await _add(
                client, uid="doc-c", doc_type="passport", file_name="passport-v1.pdf"
            )
            second = await _add(
                client, uid="doc-c", doc_type="passport", file_name="passport-v2.pdf"
            )
            listing = await client.get("/api/v1/applicant-documents/me")
    finally:
        app.dependency_overrides.clear()

    assert first["id"] == second["id"]
    assert second["file_name"] == "passport-v2.pdf"
    assert len(listing.json()) == 1


@pytest.mark.asyncio
async def test_remove_is_owner_scoped(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="doc-d")
        created = await _add(
            client, uid="doc-d", doc_type="passport", file_name="passport.pdf"
        )

        overrides(session, "applicant", uid="doc-e")
        denied = await client.delete(f"/api/v1/applicant-documents/{created['id']}")

        overrides(session, "applicant", uid="doc-d")
        allowed = await client.delete(f"/api/v1/applicant-documents/{created['id']}")
        listing = await client.get("/api/v1/applicant-documents/me")
    app.dependency_overrides.clear()

    assert denied.status_code == 404
    assert allowed.status_code == 204
    assert listing.json() == []


async def _seed_provider(session: AsyncSession, *, name: str = "Example University") -> str:
    from app.models.provider import Provider, ProviderStatus

    async with session.begin():
        provider = Provider(
            user_id="provider-owner",
            organization_name=name,
            organization_type="university",
            registration_number="REG-1",
            country="United States",
            official_website="https://example.test",
            official_email_domain="example.test",
            physical_address="1 Example Way",
            contact_person="Jordan Rivers",
            contact_phone="+15555550100",
            status=ProviderStatus.verified,
            risk_score=0,
        )
        session.add(provider)
        await session.flush()
        provider_id = str(provider.id)
    return provider_id


async def _grant_third_party_sharing_consent(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/privacy/consents",
        json={"type": "thirdPartySharing", "policy_version": "2026-01"},
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_grant_provider_access_is_owner_scoped(session: AsyncSession) -> None:
    provider_id = await _seed_provider(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="doc-f")
        created = await _add(
            client, uid="doc-f", doc_type="passport", file_name="passport.pdf"
        )
        await _grant_third_party_sharing_consent(client)

        overrides(session, "applicant", uid="doc-g")
        await _grant_third_party_sharing_consent(client)
        denied = await client.post(
            f"/api/v1/applicant-documents/{created['id']}/share",
            json={"provider_id": provider_id},
        )

        overrides(session, "applicant", uid="doc-f")
        allowed = await client.post(
            f"/api/v1/applicant-documents/{created['id']}/share",
            json={"provider_id": provider_id},
        )
        # sharing with the same provider twice is idempotent, not duplicated
        again = await client.post(
            f"/api/v1/applicant-documents/{created['id']}/share",
            json={"provider_id": provider_id},
        )
    app.dependency_overrides.clear()

    assert denied.status_code == 404
    assert allowed.status_code == 200
    assert allowed.json()["shared_with_provider_ids"] == [provider_id]
    assert again.json()["shared_with_provider_ids"] == [provider_id]


@pytest.mark.asyncio
async def test_grant_provider_access_blocked_without_consent(
    session: AsyncSession,
) -> None:
    provider_id = await _seed_provider(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="doc-no-consent")
        created = await _add(
            client, uid="doc-no-consent", doc_type="passport", file_name="passport.pdf"
        )
        response = await client.post(
            f"/api/v1/applicant-documents/{created['id']}/share",
            json={"provider_id": provider_id},
        )
        listing = await client.get("/api/v1/applicant-documents/me")
    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "consent" in response.json()["error"]["message"].lower()
    assert listing.json()[0]["shared_with_provider_ids"] == []


@pytest.mark.asyncio
async def test_grant_provider_access_blocked_after_consent_withdrawn(
    session: AsyncSession,
) -> None:
    provider_id = await _seed_provider(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="doc-withdrawn")
        created = await _add(
            client, uid="doc-withdrawn", doc_type="passport", file_name="passport.pdf"
        )
        await _grant_third_party_sharing_consent(client)
        withdraw = await client.post("/api/v1/privacy/consents/thirdPartySharing/withdraw")
        assert withdraw.status_code == 204
        response = await client.post(
            f"/api/v1/applicant-documents/{created['id']}/share",
            json={"provider_id": provider_id},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_withdrawing_consent_revokes_existing_provider_shares(
    session: AsyncSession,
) -> None:
    provider_id = await _seed_provider(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="doc-revoke")
        created = await _add(
            client, uid="doc-revoke", doc_type="passport", file_name="passport.pdf"
        )
        await _grant_third_party_sharing_consent(client)
        shared = await client.post(
            f"/api/v1/applicant-documents/{created['id']}/share",
            json={"provider_id": provider_id},
        )
        assert shared.json()["shared_with_provider_ids"] == [provider_id]

        withdraw = await client.post("/api/v1/privacy/consents/thirdPartySharing/withdraw")
        assert withdraw.status_code == 204

        listing = await client.get("/api/v1/applicant-documents/me")
    app.dependency_overrides.clear()

    assert listing.json()[0]["shared_with_provider_ids"] == []


@pytest.mark.asyncio
async def test_grant_provider_access_rejects_unknown_provider(
    session: AsyncSession,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="doc-unknown-provider")
        created = await _add(
            client,
            uid="doc-unknown-provider",
            doc_type="passport",
            file_name="passport.pdf",
        )
        await _grant_third_party_sharing_consent(client)
        response = await client.post(
            f"/api/v1/applicant-documents/{created['id']}/share",
            json={"provider_id": "00000000-0000-0000-0000-000000000000"},
        )
        malformed = await client.post(
            f"/api/v1/applicant-documents/{created['id']}/share",
            json={"provider_id": "not-a-uuid"},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert malformed.status_code == 404


@pytest.mark.asyncio
async def test_invalid_document_type_is_rejected(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="doc-h")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/applicant-documents",
                json={
                    "type": "not-a-real-type",
                    "file_name": "x.pdf",
                    "storage_path": "applicant-documents/doc-h/x.pdf",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_applicant_documents_require_authentication(session: AsyncSession) -> None:
    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = database
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/applicant-documents/me")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
