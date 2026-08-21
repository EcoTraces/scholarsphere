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


def _good_report() -> dict:
    return {
        "checks": [
            {
                "id": "check-1",
                "category": "unit",
                "outcome": "passed",
                "critical": True,
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "details": "ok",
            }
        ],
        "coverage_percent": 85,
        "mandatory_eligibility_coverage_percent": 100,
        "security_findings": [],
    }


def _artifact(version: str) -> dict:
    return {
        "version": version,
        "commit_sha": "abc123",
        "image_reference": "registry/app:abc123",
        "release_notes": "Notes",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "migration_ids": [],
    }


@pytest.mark.asyncio
async def test_quality_report_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/release/quality-reports/1.0.0")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_quality_report_requires_administrator(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/release/quality-reports/1.0.0")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_quality_report_round_trip_and_production_ready(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        missing = await client.get("/api/v1/release/quality-reports/9.9.9")
        assert missing.status_code == 200
        assert missing.json() is None
        await session.commit()

        saved = await client.put(
            "/api/v1/release/quality-reports/1.0.0", json=_good_report()
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["production_ready"] is True


@pytest.mark.asyncio
async def test_deployment_blocked_until_quality_gates_pass(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator", uid="release-admin")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        blocked = await client.post(
            "/api/v1/release/deployments",
            json={
                "artifact": _artifact("2.0.0"),
                "environment": "staging",
                "strategy": "standard",
            },
        )
        assert blocked.status_code == 409

        await client.put("/api/v1/release/quality-reports/2.0.0", json=_good_report())
        await session.commit()

        allowed = await client.post(
            "/api/v1/release/deployments",
            json={
                "artifact": _artifact("2.0.0"),
                "environment": "staging",
                "strategy": "standard",
            },
        )
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_production_deployment_requires_second_administrator_approval(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator", uid="release-admin-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.put("/api/v1/release/quality-reports/3.0.0", json=_good_report())
        await session.commit()

        created = await client.post(
            "/api/v1/release/deployments",
            json={
                "artifact": _artifact("3.0.0"),
                "environment": "production",
                "strategy": "canary",
            },
        )
        assert created.status_code == 200, created.text
        assert created.json()["status"] == "awaitingApproval"
        deployment_id = created.json()["id"]
        await session.commit()

        self_approve = await client.post(
            f"/api/v1/release/deployments/{deployment_id}/approve"
        )
        assert self_approve.status_code == 409
        await session.commit()

    overrides(session, "administrator", uid="release-admin-b")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        approved = await client.post(
            f"/api/v1/release/deployments/{deployment_id}/approve"
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "approved"
        await session.commit()

        deployed = await client.post(f"/api/v1/release/deployments/{deployment_id}/deploy")
        assert deployed.status_code == 200
        assert deployed.json()["status"] == "completed"
        await session.commit()

        rolled_back = await client.post(
            f"/api/v1/release/deployments/{deployment_id}/rollback"
        )
        assert rolled_back.status_code == 200
        assert rolled_back.json()["status"] == "rolledBack"
        await session.commit()

        history = await client.get("/api/v1/release/deployments")
        assert len(history.json()) == 1
