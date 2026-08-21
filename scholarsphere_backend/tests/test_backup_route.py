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
async def test_policy_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/backup/policy")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_policy_requires_security_administrator(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/backup/policy")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_policy_rejects_targets_beyond_maximums(session: AsyncSession) -> None:
    overrides(session, "securityAdministrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.put(
            "/api/v1/backup/policy",
            json={"recovery_point_objective_seconds": 1000},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_verify_and_list_backups(session: AsyncSession) -> None:
    overrides(session, "securityAdministrator", uid="backup-admin")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/backup/backups",
            json={"type": "fullDatabase", "region": "us-east"},
        )
        assert created.status_code == 200, created.text
        assert created.json()["status"] == "completed"
        assert created.json()["encrypted"] is True
        backup_id = created.json()["id"]
        await session.commit()

        verified = await client.post(f"/api/v1/backup/backups/{backup_id}/verify")
        assert verified.status_code == 200
        assert verified.json()["status"] == "verified"
        await session.commit()

        listed = await client.get("/api/v1/backup/backups")
        assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_verify_unknown_backup_returns_404(session: AsyncSession) -> None:
    overrides(session, "securityAdministrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/backup/backups/missing/verify")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_test_recovery_creates_recovery_record(session: AsyncSession) -> None:
    overrides(session, "securityAdministrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/backup/backups",
            json={"type": "incremental", "region": "eu-west"},
        )
        backup_id = created.json()["id"]
        await session.commit()

        test = await client.post(f"/api/v1/backup/backups/{backup_id}/test-recovery")
        assert test.status_code == 200, test.text
        assert test.json()["integrity_valid"] is True
        assert test.json()["backup_id"] == backup_id


@pytest.mark.asyncio
async def test_disaster_recovery_plan_returns_static_content(
    session: AsyncSession,
) -> None:
    overrides(session, "superAdministrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/backup/disaster-recovery-plan")
        assert response.status_code == 200
        assert len(response.json()["restoration_steps"]) == 5
        assert "security-lead" in response.json()["emergency_contacts"]
