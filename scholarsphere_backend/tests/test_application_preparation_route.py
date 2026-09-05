import uuid
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
from app.models.application import Application, ApplicationStage
from app.models.external_opportunity import ExternalOpportunity, OpportunitySource
from app.models.premium_billing import BillingInterval, Entitlement, EntitlementStatus, PremiumFeature, PremiumPlan
from app.services.parsing import utc_now


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


def user(uid: str = "applicant-1") -> AuthenticatedUser:
    return AuthenticatedUser(
        uid=uid, email=f"{uid}@example.test", email_verified=True, role="applicant", permissions=frozenset()
    )


def overrides(session: AsyncSession, *, uid: str = "applicant-1") -> None:
    async def current_user() -> AuthenticatedUser:
        return user(uid)

    async def database() -> AsyncIterator[AsyncSession]:
        # Mirrors app/db/session.py::get_db's own try/finally exactly - a
        # request that raises must still close out its transaction before
        # this shared, reused-across-requests test session serves the next
        # request (production never hits this: every real request gets its
        # own fresh AsyncSessionFactory() session).
        try:
            yield session
        finally:
            await session.rollback()

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


async def _seed_application(session: AsyncSession, *, uid: str = "applicant-1") -> Application:
    source = OpportunitySource(
        id=uuid.uuid4(),
        source_code="test_source",
        source_name="Test Source",
        source_type="government",
        base_url="https://example.org",
        authentication_type="none",
        trust_level="web_scraped",
    )
    session.add(source)
    await session.flush()
    opportunity = ExternalOpportunity(
        id=uuid.uuid4(),
        source_id=source.id,
        external_id="ext-1",
        title="Commonwealth Scholarship",
        opportunity_type="scholarship",
        provider_name="Commonwealth Scholarship Commission",
        description=(
            "Applicants must hold a first degree with at least upper second class "
            "honours. Applicants must have at least 2 years of relevant work experience. "
            "An IELTS score is required for all applicants."
        ),
        opportunity_status="posted",
        payload_hash="hash1",
        external_fingerprint="fp1",
        collected_at=utc_now(),
        last_external_update_at=utc_now(),
    )
    session.add(opportunity)
    await session.flush()
    application = Application(
        id=uuid.uuid4(),
        user_id=uid,
        opportunity_id=opportunity.id,
        opportunity_title=opportunity.title,
        provider_name=opportunity.provider_name,
        stage=ApplicationStage.saved,
    )
    session.add(application)
    await session.commit()
    return application


async def _seed_entitlement(session: AsyncSession, *, uid: str = "applicant-1") -> Entitlement:
    plan = PremiumPlan(
        id=uuid.uuid4(),
        code="complete_premium",
        name="Complete Premium",
        price_cents=10000,
        currency="USD",
        billing_interval=BillingInterval.one_time,
        features=[f.value for f in PremiumFeature],
    )
    session.add(plan)
    await session.flush()
    entitlement = Entitlement(
        id=uuid.uuid4(),
        user_id=uid,
        plan_id=plan.id,
        feature_keys=[f.value for f in PremiumFeature],
        status=EntitlementStatus.active,
    )
    session.add(entitlement)
    await session.commit()
    return entitlement


@pytest.mark.asyncio
async def test_free_user_cannot_create_workspace(session: AsyncSession) -> None:
    """CRITICAL: FREE USER -> protected feature denied."""
    application = await _seed_application(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/application-preparation/workspaces",
            json={"application_id": str(application.id), "category": "postgraduate"},
        )
        assert response.status_code == 402


@pytest.mark.asyncio
async def test_paid_user_full_workspace_flow(session: AsyncSession) -> None:
    """CRITICAL: PAID USER -> protected feature allowed. Exercises workspace

    creation, requirement matching against real opportunity text, readiness
    scoring, and the auto-generated checklist end to end.
    """
    application = await _seed_application(session)
    await _seed_entitlement(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/application-preparation/workspaces",
            json={
                "application_id": str(application.id),
                "category": "postgraduate",
                "target_university": "University of Oxford",
                "target_program": "MSc Data Science",
            },
        )
        assert create.status_code == 201
        workspace_id = create.json()["id"]
        assert create.json()["category"] == "postgraduate"

        matches = await client.get(
            f"/api/v1/application-preparation/workspaces/{workspace_id}/requirement-matches"
        )
        assert matches.status_code == 200
        assert len(matches.json()) >= 1
        statuses = {m["status"] for m in matches.json()}
        assert all(s in {"match", "partial_match", "missing", "needs_verification"} for s in statuses)
        # No applicant profile exists yet, so nothing should be auto-asserted
        # as a confident "match" from free text alone.
        assert "match" not in statuses

        readiness = await client.get(
            f"/api/v1/application-preparation/workspaces/{workspace_id}/readiness"
        )
        assert readiness.status_code == 200
        body = readiness.json()
        assert 0 <= body["overall_pct"] <= 100
        assert abs(sum(body["weights"].values()) - 1.0) < 1e-6

        checklist = await client.get(
            f"/api/v1/application-preparation/workspaces/{workspace_id}/checklist"
        )
        assert checklist.status_code == 200
        assert len(checklist.json()) > 0
        item_id = checklist.json()[0]["id"]

        update = await client.patch(
            f"/api/v1/application-preparation/workspaces/{workspace_id}/checklist/{item_id}",
            json={"status": "done"},
        )
        assert update.status_code == 200
        assert update.json()["status"] == "done"


@pytest.mark.asyncio
async def test_expired_entitlement_denied(session: AsyncSession) -> None:
    """CRITICAL: EXPIRED ENTITLEMENT -> protected feature denied."""
    application = await _seed_application(session)
    entitlement = await _seed_entitlement(session)
    entitlement.expires_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    await session.commit()
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/application-preparation/workspaces",
            json={"application_id": str(application.id), "category": "postgraduate"},
        )
        assert response.status_code == 402


@pytest.mark.asyncio
async def test_cannot_create_workspace_for_unowned_application(session: AsyncSession) -> None:
    application = await _seed_application(session, uid="other-user")
    await _seed_entitlement(session, uid="applicant-1")
    overrides(session, uid="applicant-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/application-preparation/workspaces",
            json={"application_id": str(application.id), "category": "postgraduate"},
        )
        assert response.status_code == 404
