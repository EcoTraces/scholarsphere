from collections.abc import AsyncIterator
from datetime import date

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


async def _import_one(session: AsyncSession, *, external_id: str, title: str) -> str:
    record = NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id=external_id,
        title=title,
        opportunity_type="grant",
        provider_name="Department of Education",
        country="United States",
        deadline=date(2027, 1, 1),
        opportunity_status="posted",
        official_source_url=f"https://example.test/{external_id}",
        official_application_url=f"https://example.test/{external_id}/apply",
        raw_payload={
            "id": external_id,
            "title": title,
            "agencyName": "Department of Education",
            "openDate": "07/01/2026",
            "closeDate": "01/01/2027",
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


@pytest.mark.asyncio
async def test_record_view_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.post(
            "/api/v1/analytics/opportunity-views",
            json={"opportunity_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_record_view_rejects_unknown_opportunity(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="viewer-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/analytics/opportunity-views",
            json={"opportunity_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_record_view_and_counts_require_staff(session: AsyncSession) -> None:
    opportunity_id = await _import_one(session, external_id="an-1", title="Analytics grant")

    overrides(session, "applicant", uid="viewer-b")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        recorded = await client.post(
            "/api/v1/analytics/opportunity-views",
            json={"opportunity_id": opportunity_id},
        )
        assert recorded.status_code == 204
        await session.commit()
        recorded_again = await client.post(
            "/api/v1/analytics/opportunity-views",
            json={"opportunity_id": opportunity_id},
        )
        assert recorded_again.status_code == 204
        await session.commit()

        forbidden = await client.get("/api/v1/analytics/opportunity-views")
        assert forbidden.status_code == 403

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        counts = await client.get("/api/v1/analytics/opportunity-views")
        assert counts.status_code == 200, counts.text
        assert counts.json()[opportunity_id] == 2
