import uuid
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
from app.models.premium_billing import AIUsageRecord, AIUsageStatus, BillingInterval, PremiumPlan


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


def user(role: str, uid: str = "user-1") -> AuthenticatedUser:
    return AuthenticatedUser(
        uid=uid, email=f"{uid}@example.test", email_verified=True, role=role, permissions=frozenset()
    )


def overrides(session: AsyncSession, *, role: str, uid: str = "user-1") -> None:
    async def current_user() -> AuthenticatedUser:
        return user(role, uid)

    async def database() -> AsyncIterator[AsyncSession]:
        try:
            yield session
        finally:
            await session.rollback()

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


@pytest.mark.asyncio
async def test_applicant_cannot_access_admin_routes(session: AsyncSession) -> None:
    overrides(session, role="applicant")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/premium/admin/plans")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_create_and_update_plan(session: AsyncSession) -> None:
    overrides(session, role="administrator", uid="admin-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium/admin/plans",
            json={
                "code": "cv_ats_only",
                "name": "CV / ATS Package",
                "description": "CV builder and ATS optimization only.",
                "price_cents": 3500,
                "currency": "USD",
                "billing_interval": "one_time",
                "features": ["cv_builder", "ats_optimization", "pdf_export"],
                "is_active": True,
                "sort_order": 1,
            },
        )
        assert create.status_code == 201
        plan_id = create.json()["id"]
        assert create.json()["price_cents"] == 3500

        duplicate = await client.post(
            "/api/v1/premium/admin/plans",
            json={
                "code": "cv_ats_only",
                "name": "Duplicate",
                "price_cents": 100,
                "features": [],
            },
        )
        assert duplicate.status_code == 409

        update = await client.patch(
            f"/api/v1/premium/admin/plans/{plan_id}", json={"price_cents": 4000, "is_active": False}
        )
        assert update.status_code == 200
        assert update.json()["price_cents"] == 4000
        assert update.json()["is_active"] is False

        listing = await client.get("/api/v1/premium/admin/plans")
        assert listing.status_code == 200
        assert any(p["code"] == "cv_ats_only" for p in listing.json())


@pytest.mark.asyncio
async def test_admin_usage_limits_upsert(session: AsyncSession) -> None:
    overrides(session, role="administrator", uid="admin-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        upsert = await client.put(
            "/api/v1/premium/admin/usage-limits",
            json={"feature": "sop", "plan_code": None, "limit_per_day": 5, "limit_per_month": 40},
        )
        assert upsert.status_code == 200
        assert upsert.json()["limit_per_day"] == 5

        update = await client.put(
            "/api/v1/premium/admin/usage-limits",
            json={"feature": "sop", "plan_code": None, "limit_per_day": 10, "limit_per_month": 40},
        )
        assert update.status_code == 200
        assert update.json()["limit_per_day"] == 10

        listing = await client.get("/api/v1/premium/admin/usage-limits")
        assert len(listing.json()) == 1


@pytest.mark.asyncio
async def test_admin_ai_usage_and_revenue_summary(session: AsyncSession) -> None:
    plan = PremiumPlan(
        id=uuid.uuid4(),
        code="complete_premium",
        name="Complete Premium",
        price_cents=10000,
        currency="USD",
        billing_interval=BillingInterval.one_time,
        features=[],
    )
    session.add(plan)
    session.add(
        AIUsageRecord(
            id=uuid.uuid4(),
            user_id="applicant-1",
            feature="sop",
            provider="openai",
            model="gpt-test",
            tokens_used=100,
            status=AIUsageStatus.success,
        )
    )
    session.add(
        AIUsageRecord(
            id=uuid.uuid4(),
            user_id="applicant-1",
            feature="sop",
            provider="openai",
            model="gpt-test",
            tokens_used=None,
            status=AIUsageStatus.failed,
        )
    )
    await session.commit()

    overrides(session, role="administrator", uid="admin-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        usage = await client.get("/api/v1/premium/admin/ai-usage")
        assert usage.status_code == 200
        by_status = {(row["feature"], row["status"]): row["count"] for row in usage.json()}
        assert by_status[("sop", "success")] == 1
        assert by_status[("sop", "failed")] == 1

        revenue = await client.get("/api/v1/premium/admin/revenue")
        assert revenue.status_code == 200
        assert revenue.json()["total_successful_payments"] == 0
        assert revenue.json()["total_revenue_cents"] == 0
