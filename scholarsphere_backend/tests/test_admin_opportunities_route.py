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
async def test_admin_opportunities_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/external-opportunities/opportunities")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_admin_opportunities_rejects_non_admin_roles(session: AsyncSession) -> None:
    overrides(session, "verificationOfficer")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/external-opportunities/opportunities")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_opportunities_lists_every_status(session: AsyncSession) -> None:
    pending_id = await _import_one(session, external_id="admin-1", title="Pending grant")

    verified_id = await _import_one(session, external_id="admin-2", title="Verified grant")
    overrides(session, "verificationOfficer")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        verify = await client.post(
            f"/api/v1/external-opportunities/opportunities/{verified_id}/verification",
            json={
                "decision": "approved",
                "notes": "Official source confirmed.",
                "source_checked": True,
                "application_link_checked": True,
                "deadline_checked": True,
                "duplicate_checked": True,
            },
        )
        assert verify.status_code == 200, verify.text
        await session.commit()

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/external-opportunities/opportunities")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 2
        ids_and_status = {
            item["id"]: item["verification_status"] for item in body["items"]
        }
        assert ids_and_status[pending_id] == "pending"
        assert ids_and_status[verified_id] == "verified"


@pytest.mark.asyncio
async def test_admin_opportunities_paginates(session: AsyncSession) -> None:
    for index in range(3):
        await _import_one(session, external_id=f"admin-page-{index}", title=f"Grant {index}")

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first_page = await client.get(
            "/api/v1/external-opportunities/opportunities",
            params={"page": 1, "page_size": 2},
        )
        assert first_page.status_code == 200
        assert len(first_page.json()["items"]) == 2
        assert first_page.json()["total"] == 3

        second_page = await client.get(
            "/api/v1/external-opportunities/opportunities",
            params={"page": 2, "page_size": 2},
        )
        assert len(second_page.json()["items"]) == 1
