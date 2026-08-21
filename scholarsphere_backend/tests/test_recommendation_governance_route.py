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


@pytest.mark.asyncio
async def test_controls_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/recommendations/controls")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_controls_defaults_then_save_round_trips(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="rec-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        defaults = await client.get("/api/v1/recommendations/controls")
        assert defaults.status_code == 200
        assert defaults.json()["behavioural_recommendations_enabled"] is True
        assert defaults.json()["preferred_countries"] == []
        await session.commit()

        saved = await client.put(
            "/api/v1/recommendations/controls",
            json={
                "behavioural_recommendations_enabled": False,
                "preferred_countries": ["Canada", "Germany"],
                "opportunity_categories": ["fullyFunded", "online"],
                "hidden_opportunity_ids": ["opp-1"],
            },
        )
        assert saved.status_code == 200, saved.text
        await session.commit()

        fetched = await client.get("/api/v1/recommendations/controls")
        assert fetched.json()["preferred_countries"] == ["Canada", "Germany"]
        assert fetched.json()["behavioural_recommendations_enabled"] is False


@pytest.mark.asyncio
async def test_save_controls_rejects_unknown_category(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="rec-b")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.put(
            "/api/v1/recommendations/controls",
            json={"opportunity_categories": ["notARealCategory"]},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_history_record_list_and_reset(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="rec-c")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        recorded = await client.post(
            "/api/v1/recommendations/history",
            json={
                "opportunity_id": "opp-1",
                "score": 90,
                "labels": ["strongMatch", "fullyFunded"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "host_country": "Canada",
            },
        )
        assert recorded.status_code == 204
        await session.commit()

        history = await client.get("/api/v1/recommendations/history")
        assert len(history.json()) == 1
        assert history.json()[0]["opportunity_id"] == "opp-1"
        await session.commit()

        reset = await client.delete("/api/v1/recommendations/history")
        assert reset.status_code == 204
        await session.commit()

        empty = await client.get("/api/v1/recommendations/history")
        assert empty.json() == []


@pytest.mark.asyncio
async def test_feedback_dismissal_hides_opportunity(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="rec-d")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        feedback = await client.post(
            "/api/v1/recommendations/feedback",
            json={"opportunity_id": "opp-9", "type": "dismissed"},
        )
        assert feedback.status_code == 204
        await session.commit()

        controls = await client.get("/api/v1/recommendations/controls")
        assert "opp-9" in controls.json()["hidden_opportunity_ids"]

        listed = await client.get("/api/v1/recommendations/feedback")
        assert len(listed.json()) == 1
        assert listed.json()[0]["type"] == "dismissed"


@pytest.mark.asyncio
async def test_quality_report_requires_staff_and_aggregates(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="rec-e")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/api/v1/recommendations/history",
            json={
                "opportunity_id": "opp-2",
                "score": 70,
                "labels": ["sponsoredOpportunity"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "host_country": "Japan",
            },
        )
        await session.commit()
        await client.post(
            "/api/v1/recommendations/feedback",
            json={"opportunity_id": "opp-2", "type": "helpful"},
        )
        await session.commit()

        forbidden = await client.get("/api/v1/recommendations/quality-report")
        assert forbidden.status_code == 403

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        report = await client.get("/api/v1/recommendations/quality-report")
        assert report.status_code == 200, report.text
        body = report.json()
        assert body["generated_count"] == 1
        assert body["helpful_rate"] == 1.0
        assert body["sponsored_share"] == 1.0
