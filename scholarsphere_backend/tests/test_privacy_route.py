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


async def _save_profile(client: AsyncClient, *, date_of_birth: str | None) -> None:
    payload = {"full_name": "Test User"}
    if date_of_birth is not None:
        payload["date_of_birth"] = date_of_birth
    response = await client.put("/api/v1/applicant-profiles/me", json=payload)
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_grant_and_get_consent_round_trip(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="priv-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            granted = await client.post(
                "/api/v1/privacy/consents",
                json={"type": "marketing", "policy_version": "2026-01"},
            )
            listing = await client.get("/api/v1/privacy/consents")
    finally:
        app.dependency_overrides.clear()

    assert granted.status_code == 200
    body = granted.json()
    assert body["type"] == "marketing"
    assert body["withdrawn_at"] is None
    assert len(listing.json()) == 1


@pytest.mark.asyncio
async def test_regrant_overwrites_existing_record_not_duplicates(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="priv-b")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post(
                "/api/v1/privacy/consents",
                json={"type": "cookies", "policy_version": "2026-01"},
            )
            await client.post(
                "/api/v1/privacy/consents",
                json={"type": "cookies", "policy_version": "2026-02"},
            )
            listing = await client.get("/api/v1/privacy/consents")
    finally:
        app.dependency_overrides.clear()

    assert len(listing.json()) == 1
    assert listing.json()[0]["policy_version"] == "2026-02"


@pytest.mark.asyncio
async def test_minor_cannot_grant_restricted_consent(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="priv-c")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            recent_birthdate = (date.today() - timedelta(days=365 * 10)).isoformat()
            await _save_profile(client, date_of_birth=recent_birthdate)

            restricted = await client.post(
                "/api/v1/privacy/consents",
                json={"type": "thirdPartySharing", "policy_version": "2026-01"},
            )
            allowed = await client.post(
                "/api/v1/privacy/consents",
                json={"type": "cookies", "policy_version": "2026-01"},
            )
    finally:
        app.dependency_overrides.clear()

    assert restricted.status_code == 409
    assert allowed.status_code == 200


@pytest.mark.asyncio
async def test_adult_can_grant_restricted_consent(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="priv-d")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            adult_birthdate = (date.today() - timedelta(days=365 * 30)).isoformat()
            await _save_profile(client, date_of_birth=adult_birthdate)

            response = await client.post(
                "/api/v1/privacy/consents",
                json={"type": "thirdPartySharing", "policy_version": "2026-01"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_no_profile_yet_is_treated_as_not_minor(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="priv-e")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/privacy/consents",
                json={"type": "marketing", "policy_version": "2026-01"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_client_supplied_minor_flag_is_never_trusted(session: AsyncSession) -> None:
    """The Dart interface has setMinorStatus, but the live backend computes

    is-minor itself from the real profile - there is deliberately no route
    that accepts a client-asserted minor flag at all.
    """
    overrides(session, "applicant", uid="priv-f")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            adult_birthdate = (date.today() - timedelta(days=365 * 30)).isoformat()
            await _save_profile(client, date_of_birth=adult_birthdate)
            response = await client.post(
                "/api/v1/privacy/consents",
                json={
                    "type": "thirdPartySharing",
                    "policy_version": "2026-01",
                    "is_minor": True,
                },
            )
    finally:
        app.dependency_overrides.clear()

    # extra unknown field is ignored by pydantic, real profile (adult) wins
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_required_legal_consent_cannot_be_withdrawn(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="priv-g")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post(
                "/api/v1/privacy/consents",
                json={"type": "privacyPolicy", "policy_version": "2026-01"},
            )
            response = await client.post(
                "/api/v1/privacy/consents/privacyPolicy/withdraw"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_withdraw_consent_sets_withdrawn_at(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="priv-h")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post(
                "/api/v1/privacy/consents",
                json={"type": "marketing", "policy_version": "2026-01"},
            )
            withdrawn = await client.post(
                "/api/v1/privacy/consents/marketing/withdraw"
            )
            listing = await client.get("/api/v1/privacy/consents")
    finally:
        app.dependency_overrides.clear()

    assert withdrawn.status_code == 204
    assert listing.json()[0]["withdrawn_at"] is not None


@pytest.mark.asyncio
async def test_submit_and_get_requests_is_scoped(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="priv-i")
        submitted = await client.post(
            "/api/v1/privacy/requests",
            json={"type": "dataExport", "notes": "please"},
        )

        overrides(session, "applicant", uid="priv-j")
        other_user_requests = await client.get("/api/v1/privacy/requests")

        overrides(session, "applicant", uid="priv-i")
        own_requests = await client.get("/api/v1/privacy/requests")
    app.dependency_overrides.clear()

    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"
    assert other_user_requests.json() == []
    assert len(own_requests.json()) == 1


@pytest.mark.asyncio
async def test_record_organization_access_requires_staff_and_active_consent(
    session: AsyncSession,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="priv-k")
        denied = await client.post(
            "/api/v1/privacy/access-history",
            json={
                "user_id": "priv-k",
                "organization_id": "org-1",
                "organization_name": "Acme",
                "data_categories": ["profile"],
            },
        )

        overrides(session, "administrator")
        no_consent = await client.post(
            "/api/v1/privacy/access-history",
            json={
                "user_id": "priv-k",
                "organization_id": "org-1",
                "organization_name": "Acme",
                "data_categories": ["profile"],
            },
        )

        overrides(session, "applicant", uid="priv-k")
        await client.post(
            "/api/v1/privacy/consents",
            json={"type": "thirdPartySharing", "policy_version": "2026-01"},
        )

        overrides(session, "administrator")
        recorded = await client.post(
            "/api/v1/privacy/access-history",
            json={
                "user_id": "priv-k",
                "organization_id": "org-1",
                "organization_name": "Acme",
                "data_categories": ["profile"],
            },
        )

        overrides(session, "applicant", uid="priv-k")
        history = await client.get("/api/v1/privacy/access-history")
    app.dependency_overrides.clear()

    assert denied.status_code == 403
    assert no_consent.status_code == 409
    assert recorded.status_code == 200
    assert len(history.json()) == 1


@pytest.mark.asyncio
async def test_incidents_require_staff(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant")
        denied = await client.get("/api/v1/privacy/incidents")

        overrides(session, "securityAdministrator")
        recorded = await client.post(
            "/api/v1/privacy/incidents",
            json={"summary": "Test incident", "affected_user_ids": ["priv-l"]},
        )
        listed = await client.get("/api/v1/privacy/incidents")
    app.dependency_overrides.clear()

    assert denied.status_code == 403
    assert recorded.status_code == 200
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_privacy_requires_authentication(session: AsyncSession) -> None:
    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = database
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/privacy/consents")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
