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


async def _register(
    client: AsyncClient,
    *,
    source_id: str = "src-1",
    name: str = "Example University",
    domain: str = "https://admissions.example.edu",
    trust_level: str = "e",
    accuracy_rate: float = 1.0,
) -> dict:
    response = await client.post(
        "/api/v1/source-registry",
        json={
            "id": source_id,
            "name": name,
            "type": "officialUniversityWebsite",
            "domain": domain,
            "country": "Global",
            "organization_id": "",
            "trust_level": trust_level,
            "accuracy_rate": accuracy_rate,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_source_registry_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/source-registry")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_register_computes_score_and_defaults_pending(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        body = await _register(client)
        assert body["verification_status"] == "pending"
        assert body["type"] == "officialUniversityWebsite"
        # base(e)=42, correction=0, rejection=0, accuracy 1.0 -> round((1-.8)*20)=4
        assert body["trust_score"] == 46


@pytest.mark.asyncio
async def test_register_rejects_duplicate_domain(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _register(client, source_id="src-1", domain="https://www.example.edu")
        response = await client.post(
            "/api/v1/source-registry",
            json={
                "id": "src-2",
                "name": "Different Name",
                "type": "officialUniversityWebsite",
                "domain": "http://example.edu/apply",
                "country": "Global",
                "organization_id": "",
                "trust_level": "e",
                "accuracy_rate": 1.0,
            },
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_review_updates_trust_level_and_blocks(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _register(client)
        response = await client.post(
            "/api/v1/source-registry/src-1/review",
            json={"trust_level": "a", "status": "approved"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["trust_level"] == "a"
        assert body["verification_status"] == "approved"
        assert body["is_blocked"] is False
        assert body["trust_score"] == 99  # base(a)=95 + round((1-.8)*20)=4

        blocked = await client.post(
            "/api/v1/source-registry/src-1/review",
            json={"trust_level": "f", "status": "blocked"},
        )
        assert blocked.json()["is_blocked"] is True


@pytest.mark.asyncio
async def test_approved_source_for_matches_subdomain_and_requires_approval(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _register(client, domain="https://example.edu")
        none_yet = await client.get(
            "/api/v1/source-registry/approved", params={"location": "apply.example.edu"}
        )
        assert none_yet.json() is None
        await session.commit()

        await client.post(
            "/api/v1/source-registry/src-1/review",
            json={"trust_level": "a", "status": "approved"},
        )
        found = await client.get(
            "/api/v1/source-registry/approved", params={"location": "apply.example.edu"}
        )
        assert found.status_code == 200
        assert found.json()["id"] == "src-1"


@pytest.mark.asyncio
async def test_record_access_tracks_rejections_and_last_checked(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _register(client)
        failed = await client.post(
            "/api/v1/source-registry/src-1/access", json={"successful": False}
        )
        assert failed.status_code == 200
        body = failed.json()
        assert body["rejection_count"] == 1
        assert body["last_checked_at"] is not None
        assert body["last_successful_access"] is None

        ok = await client.post(
            "/api/v1/source-registry/src-1/access", json={"successful": True}
        )
        assert ok.json()["last_successful_access"] is not None


@pytest.mark.asyncio
async def test_record_correction_increments_count_and_penalizes_score(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        registered = await _register(client)
        response = await client.post("/api/v1/source-registry/src-1/correction")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["correction_count"] == 1
        assert body["trust_score"] == registered["trust_score"] - 3


@pytest.mark.asyncio
async def test_record_access_and_correction_404_for_unknown_source(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/source-registry/missing/access", json={"successful": True}
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_all_sorted_by_name(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _register(
            client, source_id="src-z", name="Zeta University", domain="https://zeta.edu"
        )
        await _register(
            client, source_id="src-a", name="Alpha University", domain="https://alpha.edu"
        )
        response = await client.get("/api/v1/source-registry")
        names = [item["name"] for item in response.json()]
        assert names == ["Alpha University", "Zeta University"]
