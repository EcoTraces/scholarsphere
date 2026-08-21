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
from app.models.source_registry import ReliabilityLevel, SourceRegistryEntry, SourceVerificationStatus
from app.services.parsing import utc_now


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


def _payload(**overrides_kwargs: object) -> dict:
    payload = {
        "title": "Collected opportunity awaiting review",
        "provider": "Unconfirmed sponsor",
        "host_country": "Global",
        "type": "scholarship",
        "deadline": (date.today() + timedelta(days=90)).isoformat(),
        "application_open_date": date.today().isoformat(),
        "official_source_url": "https://example.test/opportunity",
        "application_url": "https://example.test/opportunity/apply",
        "summary": "Collected source awaiting verification and enrichment.",
        "source_type": "manualAdministrator",
        "source_location": "https://example.test/opportunity",
        "approved_source": True,
    }
    payload.update(overrides_kwargs)
    return payload


@pytest.mark.asyncio
async def test_collect_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.post("/api/v1/collection/collect", json=_payload())
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_collect_requires_administration_role(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/collection/collect", json=_payload())
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_manual_collection_creates_pending_opportunity_and_ledger_entry(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator", uid="collector-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/collection/collect", json=_payload())
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["verification_status"] == "pending"
        assert body["automated"] is False
        assert body["collected_by_user_id"] == "collector-a"
        await session.commit()

        ledger = await client.get("/api/v1/collection/ledger")
        assert len(ledger.json()) == 1
        assert ledger.json()[0]["opportunity_id"] == body["opportunity_id"]


@pytest.mark.asyncio
async def test_automated_collection_requires_approved_registry_source(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        rejected = await client.post(
            "/api/v1/collection/collect",
            json=_payload(
                source_type="approvedRss",
                source_location="https://unregistered.example/feed",
            ),
        )
        assert rejected.status_code == 409


@pytest.mark.asyncio
async def test_automated_collection_succeeds_for_approved_registry_source(
    session: AsyncSession,
) -> None:
    async with session.begin():
        now = utc_now()
        session.add(
            SourceRegistryEntry(
                id="src-1",
                name="Trusted RSS",
                type="approved_rss_feed",
                domain="trusted.example",
                normalized_domain="trusted.example",
                trust_level=ReliabilityLevel.a,
                trust_score=95,
                verification_status=SourceVerificationStatus.approved,
                is_blocked=False,
                created_at=now,
                updated_at=now,
            )
        )
    await session.commit()

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        allowed = await client.post(
            "/api/v1/collection/collect",
            json=_payload(
                source_type="approvedRss",
                source_location="https://trusted.example/feed.xml",
                approved_source=False,
            ),
        )
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()["automated"] is True
        assert allowed.json()["approved_source"] is True
