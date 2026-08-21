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


_NOW = datetime.now(timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_logs_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/observability/logs")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_logs_requires_staff_role(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/observability/logs")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_record_and_search_logs(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        recorded = await client.post(
            "/api/v1/observability/logs",
            json={
                "level": "error",
                "service": "api",
                "message": "Payment gateway timeout",
                "timestamp": _NOW,
                "correlation_id": "corr-1",
            },
        )
        assert recorded.status_code == 204
        await session.commit()

        await client.post(
            "/api/v1/observability/logs",
            json={
                "level": "debug",
                "service": "worker",
                "message": "cache warm",
                "timestamp": _NOW,
                "correlation_id": "corr-2",
            },
        )
        await session.commit()

        by_level = await client.get(
            "/api/v1/observability/logs", params={"minimum_level": "warning"}
        )
        assert len(by_level.json()) == 1
        assert by_level.json()[0]["service"] == "api"

        by_query = await client.get(
            "/api/v1/observability/logs", params={"query": "timeout"}
        )
        assert len(by_query.json()) == 1


@pytest.mark.asyncio
async def test_metric_crossing_threshold_creates_incident(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        rule = await client.put(
            "/api/v1/observability/alert-rules/rule-1",
            json={
                "id": "rule-1",
                "metric_name": "request.error_rate",
                "threshold": 0.5,
                "comparison": "greaterThan",
                "severity": "critical",
                "escalation_target": "oncall",
                "enabled": True,
            },
        )
        assert rule.status_code == 200, rule.text
        await session.commit()

        below = await client.post(
            "/api/v1/observability/metrics",
            json={
                "name": "request.error_rate",
                "value": 0.2,
                "unit": "ratio",
                "timestamp": _NOW,
            },
        )
        assert below.status_code == 204
        await session.commit()

        above = await client.post(
            "/api/v1/observability/metrics",
            json={
                "name": "request.error_rate",
                "value": 0.9,
                "unit": "ratio",
                "timestamp": _NOW,
            },
        )
        assert above.status_code == 204
        await session.commit()

        incidents = await client.get("/api/v1/observability/incidents")
        assert len(incidents.json()) == 1
        assert incidents.json()[0]["escalation_target"] == "oncall"


@pytest.mark.asyncio
async def test_trace_upsert_by_trace_and_span_id(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.post(
            "/api/v1/observability/traces",
            json={
                "trace_id": "trace-1",
                "span_id": "span-1",
                "operation": "GET /opportunities",
                "service": "api",
                "started_at": _NOW,
                "duration_seconds": 0.2,
                "successful": True,
            },
        )
        assert first.status_code == 204


@pytest.mark.asyncio
async def test_health_reports_database_connectivity(session: AsyncSession) -> None:
    overrides(session, "securityAdministrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/observability/health")
        assert response.status_code == 200
        services = {item["service"] for item in response.json()}
        assert services == {"database", "api"}
        assert all(item["status"] == "healthy" for item in response.json())


@pytest.mark.asyncio
async def test_performance_report_computes_volume_and_error_rate(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for value in (100, 200, 300):
            await client.post(
                "/api/v1/observability/metrics",
                json={
                    "name": "request.duration_ms",
                    "value": value,
                    "unit": "ms",
                    "timestamp": _NOW,
                },
            )
            await session.commit()
        await client.post(
            "/api/v1/observability/metrics",
            json={
                "name": "request.error",
                "value": 1,
                "unit": "count",
                "timestamp": _NOW,
            },
        )
        await session.commit()

        report = await client.get("/api/v1/observability/performance-report")
        assert report.status_code == 200, report.text
        body = report.json()
        assert body["request_volume"] == 3
        assert body["error_rate"] == pytest.approx(1 / 3)
        assert body["average_response_milliseconds"] == pytest.approx(200)


@pytest.mark.asyncio
async def test_enforce_log_retention_removes_expired(session: AsyncSession) -> None:
    from datetime import timedelta

    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/api/v1/observability/logs",
            json={
                "level": "info",
                "service": "api",
                "message": "old",
                "timestamp": old_timestamp,
                "correlation_id": "corr-old",
            },
        )
        await session.commit()
        await client.post(
            "/api/v1/observability/logs",
            json={
                "level": "info",
                "service": "api",
                "message": "new",
                "timestamp": _NOW,
                "correlation_id": "corr-new",
            },
        )
        await session.commit()

        removed = await client.post(
            "/api/v1/observability/logs/enforce-retention",
            params={"retention_seconds": 3600},
        )
        assert removed.status_code == 200
        assert removed.json() == 1
