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
async def test_create_case_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.post(
            "/api/v1/fraud-investigation/cases",
            json={"subject_type": "user", "subject_id": "user-1"},
        )
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_create_case_requires_staff_role(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/fraud-investigation/cases",
            json={"subject_type": "user", "subject_id": "user-1"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_case_computes_risk_and_rejects_duplicate(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator", uid="fraud-officer-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/fraud-investigation/cases",
            json={
                "subject_type": "user",
                "subject_id": "user-low-risk",
                "risk_input": {"provider_risk": 10},
            },
        )
        assert created.status_code == 200, created.text
        assert created.json()["risk"]["level"] == "low"
        assert created.json()["status"] == "opened"
        await session.commit()

        duplicate = await client.post(
            "/api/v1/fraud-investigation/cases",
            json={"subject_type": "user", "subject_id": "user-low-risk"},
        )
        assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_critical_risk_automatically_restricts_opportunity(
    session: AsyncSession,
) -> None:
    opportunity_id = await _import_one(session, external_id="fraud-1", title="Suspicious grant")

    overrides(session, "administrator", uid="fraud-officer-b")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/fraud-investigation/cases",
            json={
                "subject_type": "opportunity",
                "subject_id": opportunity_id,
                "risk_input": {
                    "provider_risk": 100,
                    "source_risk": 100,
                    "user_behaviour_risk": 100,
                    "suspicious_domain": True,
                    "duplicate_account": True,
                    "risky_link": True,
                    "payment_request": True,
                    "impersonation": True,
                },
            },
        )
        assert created.status_code == 200, created.text
        assert created.json()["risk"]["level"] == "critical"
        assert created.json()["status"] == "restricted"
        await session.commit()

    opportunity = await session.get(ExternalOpportunity, __import__("uuid").UUID(opportunity_id))
    assert opportunity.verification_status.value == "suspicious"


@pytest.mark.asyncio
async def test_assign_note_and_restrict_workflow(session: AsyncSession) -> None:
    overrides(session, "administrator", uid="fraud-officer-c")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/fraud-investigation/cases",
            json={"subject_type": "domain", "subject_id": "scam.example"},
        )
        case_id = created.json()["id"]
        await session.commit()

        assigned = await client.post(
            f"/api/v1/fraud-investigation/cases/{case_id}/assign",
            json={"investigator_id": "fraud-officer-c"},
        )
        assert assigned.status_code == 200
        await session.commit()

        forbidden_note = await client.post(
            f"/api/v1/fraud-investigation/cases/{case_id}/notes",
            json={"note": "not the assigned investigator"},
        )
        # caller uid matches assigned investigator here, so this should succeed
        assert forbidden_note.status_code == 200
        assert forbidden_note.json()["status"] == "investigating"
        await session.commit()

        no_evidence = await client.post(f"/api/v1/fraud-investigation/cases/{case_id}/restrict")
        assert no_evidence.status_code == 409
        await session.commit()

        evidence = await client.post(
            f"/api/v1/fraud-investigation/cases/{case_id}/evidence",
            json={"type": "screenshot", "location": "s3://evidence/1.png", "summary": "proof"},
        )
        assert evidence.status_code == 200
        await session.commit()

        restricted = await client.post(f"/api/v1/fraud-investigation/cases/{case_id}/restrict")
        assert restricted.status_code == 200
        assert restricted.json()["status"] == "restricted"


@pytest.mark.asyncio
async def test_appeal_requires_matching_subject_or_staff(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/fraud-investigation/cases",
            json={
                "subject_type": "user",
                "subject_id": "restricted-user",
                "risk_input": {
                    "provider_risk": 100,
                    "source_risk": 100,
                    "user_behaviour_risk": 100,
                    "suspicious_domain": True,
                    "duplicate_account": True,
                    "risky_link": True,
                    "payment_request": True,
                    "impersonation": True,
                },
            },
        )
        case_id = created.json()["id"]
        assert created.json()["status"] == "restricted"
        await session.commit()

    overrides(session, "applicant", uid="someone-else")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        forbidden = await client.post(
            f"/api/v1/fraud-investigation/cases/{case_id}/appeal",
            json={"reason": "not me"},
        )
        assert forbidden.status_code == 403

    overrides(session, "applicant", uid="restricted-user")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        allowed = await client.post(
            f"/api/v1/fraud-investigation/cases/{case_id}/appeal",
            json={"reason": "this was a mistake"},
        )
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()["status"] == "appealed"


@pytest.mark.asyncio
async def test_watchlist_rejects_duplicate_and_blocks(session: AsyncSession) -> None:
    overrides(session, "administrator", uid="fraud-officer-d")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        added = await client.post(
            "/api/v1/fraud-investigation/watchlist",
            json={
                "subject_type": "domain",
                "value": "Scam.Example",
                "reason": "known scam domain",
            },
        )
        assert added.status_code == 204
        await session.commit()

        duplicate = await client.post(
            "/api/v1/fraud-investigation/watchlist",
            json={"subject_type": "domain", "value": "scam.example", "reason": "dup"},
        )
        assert duplicate.status_code == 409
        await session.commit()

        blocked = await client.get(
            "/api/v1/fraud-investigation/watchlist/domain/blocked",
            params={"value": "SCAM.example"},
        )
        assert blocked.json() is True


@pytest.mark.asyncio
async def test_queue_and_analytics(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/api/v1/fraud-investigation/cases",
            json={"subject_type": "payment", "subject_id": "payment-1"},
        )
        await session.commit()

        queue = await client.get("/api/v1/fraud-investigation/queue")
        assert len(queue.json()) == 1

        analytics = await client.get("/api/v1/fraud-investigation/analytics")
        assert analytics.status_code == 200, analytics.text
        assert analytics.json()["open_cases"] == 1
        assert analytics.json()["by_subject_type"] == {"payment": 1}
