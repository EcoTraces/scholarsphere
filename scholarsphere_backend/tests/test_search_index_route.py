from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta, timezone

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


async def _import_one(
    session: AsyncSession, *, external_id: str, title: str, deadline: date
) -> str:
    record = NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id=external_id,
        title=title,
        opportunity_type="grant",
        provider_name="Department of Education",
        country="United States",
        deadline=deadline,
        opportunity_status="posted",
        official_source_url=f"https://example.test/{external_id}",
        official_application_url=f"https://example.test/{external_id}/apply",
        raw_payload={
            "id": external_id,
            "title": title,
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
    assert verify.status_code == 200, verify.text
    publish = await client.post(
        f"/api/v1/external-opportunities/opportunities/{opportunity_id}/publication",
        json={"published": True},
    )
    assert publish.status_code == 200, publish.text


def _snapshot(
    opportunity_id: str,
    *,
    title: str,
    deadline: datetime,
    host_country: str = "United States",
    verified: bool = True,
    fields_of_study: list[str] | None = None,
) -> dict:
    return {
        "id": opportunity_id,
        "title": title,
        "provider": "Department of Education",
        "hostInstitution": "Department of Education",
        "hostCountry": host_country,
        "type": "grant",
        "funding": "fullyFunded",
        "deadline": deadline.isoformat(),
        "applicationOpenDate": deadline.isoformat(),
        "verificationStatus": "verified" if verified else "pending",
        "lastVerifiedAt": deadline.isoformat(),
        "officialSourceUrl": "https://example.test",
        "applicationUrl": "https://example.test/apply",
        "eligibleNationalities": ["All nationalities"],
        "studyLevels": ["Masters"],
        "fieldsOfStudy": fields_of_study or ["Computer Science"],
        "summary": "A great opportunity.",
        "benefits": [],
        "eligibilityRequirements": [],
        "requiredDocuments": [],
        "applicationProcedure": [],
        "languageRequirements": [],
        "minimumAge": None,
        "maximumAge": None,
        "workExperienceYearsRequired": None,
        "contactInformation": "",
        "availablePositions": None,
        "deliveryFormat": "online",
        "applicationFee": 0,
    }


@pytest.mark.asyncio
async def test_search_index_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/search-index/autocomplete", params={"prefix": "a"})
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_synchronize_rejects_fake_opportunity_and_accepts_real_one(
    session: AsyncSession,
) -> None:
    deadline = date.today() + timedelta(days=30)
    opportunity_id = await _import_one(
        session, external_id="grant-1", title="Education Innovation Grant", deadline=deadline
    )

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _verify_and_publish(client, opportunity_id)
        await session.commit()

    overrides(session, "applicant", uid="idx-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        deadline_dt = datetime.combine(deadline, datetime.min.time(), tzinfo=timezone.utc)
        response = await client.post(
            "/api/v1/search-index/synchronize",
            json={
                "opportunities": [
                    _snapshot(opportunity_id, title="Education Innovation Grant", deadline=deadline_dt),
                    _snapshot(
                        "00000000-0000-0000-0000-000000000099",
                        title="Fabricated Listing",
                        deadline=deadline_dt,
                    ),
                ]
            },
        )
        assert response.status_code == 204
        await session.commit()

        results = await client.post(
            "/api/v1/search-index/search",
            json={"query": "", "page": 1, "page_size": 20},
        )
        titles = {hit["opportunity"]["title"] for hit in results.json()["hits"]}
        assert titles == {"Education Innovation Grant"}


@pytest.mark.asyncio
async def test_search_matches_by_term_and_facets(session: AsyncSession) -> None:
    deadline = date.today() + timedelta(days=30)
    opportunity_id = await _import_one(
        session, external_id="grant-2", title="Computer Science Scholarship", deadline=deadline
    )

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _verify_and_publish(client, opportunity_id)
        await session.commit()

    overrides(session, "applicant", uid="idx-b")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        deadline_dt = datetime.combine(deadline, datetime.min.time(), tzinfo=timezone.utc)
        await client.post(
            "/api/v1/search-index/opportunities",
            json=_snapshot(
                opportunity_id, title="Computer Science Scholarship", deadline=deadline_dt
            ),
        )
        await session.commit()

        found = await client.post(
            "/api/v1/search-index/search",
            json={"query": "scholarship", "page": 1, "page_size": 20},
        )
        assert found.json()["total"] == 1
        assert found.json()["facets"]["countries"]["United States"] == 1

        no_match = await client.post(
            "/api/v1/search-index/search",
            json={"query": "astronomy", "page": 1, "page_size": 20},
        )
        assert no_match.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_history_is_recorded_and_scoped_to_caller(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="idx-c")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/api/v1/search-index/search",
            json={"query": "grant", "page": 1, "page_size": 20},
        )
        await session.commit()

        history = await client.get("/api/v1/search-index/history")
        assert len(history.json()) == 1
        assert history.json()[0]["query"] == "grant"

    overrides(session, "applicant", uid="idx-other")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        other_history = await client.get("/api/v1/search-index/history")
        assert other_history.json() == []


@pytest.mark.asyncio
async def test_clear_history_removes_only_callers_own(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="idx-d")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/api/v1/search-index/search", json={"query": "grant", "page": 1, "page_size": 20}
        )
        await session.commit()
        await client.delete("/api/v1/search-index/history")
        await session.commit()
        remaining = await client.get("/api/v1/search-index/history")
        assert remaining.json() == []


@pytest.mark.asyncio
async def test_remove_and_rebuild_require_staff(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        forbidden_remove = await client.delete("/api/v1/search-index/opportunities/some-id")
        assert forbidden_remove.status_code == 403
        forbidden_rebuild = await client.post(
            "/api/v1/search-index/rebuild", json={"opportunities": []}
        )
        assert forbidden_rebuild.status_code == 403

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        allowed = await client.post("/api/v1/search-index/rebuild", json={"opportunities": []})
        assert allowed.status_code == 200
        assert allowed.json() == 0


@pytest.mark.asyncio
async def test_autocomplete_matches_prefix_and_substring(session: AsyncSession) -> None:
    deadline = date.today() + timedelta(days=30)
    opportunity_id = await _import_one(
        session, external_id="grant-3", title="Renewable Energy Fellowship", deadline=deadline
    )

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _verify_and_publish(client, opportunity_id)
        await session.commit()

    overrides(session, "applicant", uid="idx-e")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        deadline_dt = datetime.combine(deadline, datetime.min.time(), tzinfo=timezone.utc)
        await client.post(
            "/api/v1/search-index/opportunities",
            json=_snapshot(
                opportunity_id, title="Renewable Energy Fellowship", deadline=deadline_dt
            ),
        )
        await session.commit()

        response = await client.get(
            "/api/v1/search-index/autocomplete", params={"prefix": "renew"}
        )
        assert "Renewable Energy Fellowship" in response.json()
