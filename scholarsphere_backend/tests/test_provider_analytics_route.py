from collections.abc import AsyncIterator
from datetime import datetime, timezone

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
    app.dependency_overrides.clear()


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


async def _register_provider(client: AsyncClient, *, uid: str) -> str:
    response = await client.post(
        "/api/v1/providers",
        json={
            "organization_name": "Global Education Foundation",
            "organization_type": "Foundation",
            "registration_number": f"GEF-{uid}",
            "country": "Global",
            "official_website": "https://education.example",
            "official_email_domain": "education.example",
            "physical_address": "International Programs Office",
            "contact_person": "Provider Administrator",
            "contact_phone": "+000000000",
            "supporting_documents": [f"provider-documents/{uid}/registration-certificate.pdf"],
            "social_media_links": [],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def _record_event(
    client: AsyncClient, *, provider_id: str, kind: str, country: str = "Kenya"
) -> None:
    response = await client.post(
        "/api/v1/provider-analytics/events",
        json={
            "provider_id": provider_id,
            "opportunity_id": "opp-1",
            "kind": kind,
            "country": country,
            "study_level": "masters",
            "field": "engineering",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 204, response.text


@pytest.mark.asyncio
async def test_record_event_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.post(
            "/api/v1/provider-analytics/events",
            json={
                "provider_id": "00000000-0000-0000-0000-000000000000",
                "opportunity_id": "opp-1",
                "kind": "view",
                "country": "Kenya",
                "study_level": "masters",
                "field": "engineering",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_record_event_rejects_unknown_provider(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="visitor-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/provider-analytics/events",
            json={
                "provider_id": "00000000-0000-0000-0000-000000000000",
                "opportunity_id": "opp-1",
                "kind": "view",
                "country": "Kenya",
                "study_level": "masters",
                "field": "engineering",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_snapshot_requires_provider_ownership(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="owner-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        provider_id = await _register_provider(client, uid="owner-a")
        await session.commit()

    overrides(session, "applicant", uid="stranger-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        forbidden = await client.get(f"/api/v1/provider-analytics/{provider_id}/snapshot")
        assert forbidden.status_code == 403

    overrides(session, "applicant", uid="owner-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        allowed = await client.get(f"/api/v1/provider-analytics/{provider_id}/snapshot")
        assert allowed.status_code == 200, allowed.text

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        staff = await client.get(f"/api/v1/provider-analytics/{provider_id}/snapshot")
        assert staff.status_code == 200


@pytest.mark.asyncio
async def test_snapshot_suppresses_small_cohorts_and_counts_kinds(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="owner-b")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        provider_id = await _register_provider(client, uid="owner-b")
        await session.commit()

        await _record_event(client, provider_id=provider_id, kind="view")
        await session.commit()
        await _record_event(client, provider_id=provider_id, kind="view")
        await session.commit()
        await _record_event(client, provider_id=provider_id, kind="save")
        await session.commit()

        small_cohort = await client.get(f"/api/v1/provider-analytics/{provider_id}/snapshot")
        body = small_cohort.json()
        assert body["views"] == 2
        assert body["saves"] == 1
        assert body["suppressed"] is True
        assert body["countries"] == {}

        export = await client.get(f"/api/v1/provider-analytics/{provider_id}/export")
        assert export.status_code == 200
        assert "views,2" in export.json()["csv"]
