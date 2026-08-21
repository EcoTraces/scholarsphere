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


def user(role: str, uid: str | None = None, email: str | None = None) -> AuthenticatedUser:
    from app.core.auth import permissions_for_role

    return AuthenticatedUser(
        uid=uid or f"{role}-user",
        email=email or f"{uid or role}@example.test",
        email_verified=True,
        role=role,
        permissions=permissions_for_role(role),
    )


def overrides(
    session: AsyncSession, role: str, uid: str | None = None, email: str | None = None
) -> None:
    async def current_user() -> AuthenticatedUser:
        return user(role, uid, email)

    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


_DEVICE = {"id": "device-1", "browser": "Chrome", "operating_system": "Windows"}


@pytest.mark.asyncio
async def test_sessions_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/security/sessions")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_privileged_session_requires_strong_authentication(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="sec-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/security/sessions",
            json={
                "device": _DEVICE,
                "strong_authentication": False,
                "privileged": True,
            },
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_list_and_revoke_own_session(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="sec-b")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/security/sessions",
            json={
                "device": _DEVICE,
                "strong_authentication": True,
                "privileged": False,
            },
        )
        assert created.status_code == 200, created.text
        session_id = created.json()["id"]
        assert created.json()["device"]["ip_address"] != ""
        await session.commit()

        listed = await client.get("/api/v1/security/sessions")
        assert len(listed.json()) == 1
        await session.commit()

        revoked = await client.delete(f"/api/v1/security/sessions/{session_id}")
        assert revoked.status_code == 204


@pytest.mark.asyncio
async def test_cannot_revoke_another_users_session(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="sec-owner")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/security/sessions",
            json={
                "device": _DEVICE,
                "strong_authentication": True,
                "privileged": False,
            },
        )
        session_id = created.json()["id"]
        await session.commit()

    overrides(session, "applicant", uid="sec-stranger")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        forbidden = await client.delete(f"/api/v1/security/sessions/{session_id}")
        assert forbidden.status_code == 404


@pytest.mark.asyncio
async def test_revoke_all_requires_ownership_or_suspend_permission(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="sec-c")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/api/v1/security/sessions",
            json={
                "device": _DEVICE,
                "strong_authentication": True,
                "privileged": False,
            },
        )
        await session.commit()

    overrides(session, "applicant", uid="sec-stranger-2")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        forbidden = await client.post("/api/v1/security/users/sec-c/sessions/revoke-all")
        assert forbidden.status_code == 403

    overrides(session, "securityAdministrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        allowed = await client.post("/api/v1/security/users/sec-c/sessions/revoke-all")
        assert allowed.status_code == 204
        await session.commit()

    overrides(session, "applicant", uid="sec-c")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        remaining = await client.get("/api/v1/security/sessions")
        assert all(item["revoked_at"] is not None for item in remaining.json())


@pytest.mark.asyncio
async def test_record_login_tracks_new_device_and_history(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="sec-d", email="sec-d@example.test")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.post(
            "/api/v1/security/login-history",
            json={"outcome": "success", "device": _DEVICE},
        )
        assert first.status_code == 204
        await session.commit()

        history = await client.get("/api/v1/security/login-history")
        assert len(history.json()) == 1
        assert history.json()[0]["suspicious"] is False
        await session.commit()

        second_device = {
            "id": "device-2",
            "browser": "Safari",
            "operating_system": "macOS",
        }
        second = await client.post(
            "/api/v1/security/login-history",
            json={"outcome": "success", "device": second_device},
        )
        assert second.status_code == 204
        await session.commit()

        alerts = await client.get("/api/v1/security/alerts")
        # The very first login also raises a (non-suspicious) newDevice
        # alert since there is no prior device to compare against yet -
        # matches DemoSecurityRepository.recordLogin's semantics.
        types = [item["type"] for item in alerts.json()]
        assert types == ["newDevice", "suspiciousLogin"]


@pytest.mark.asyncio
async def test_login_history_and_alerts_are_scoped_to_caller(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="sec-e", email="sec-e@example.test")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/api/v1/security/login-history",
            json={"outcome": "success", "device": _DEVICE},
        )
        await session.commit()

    overrides(session, "applicant", uid="sec-f", email="sec-f@example.test")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        other_history = await client.get("/api/v1/security/login-history")
        assert other_history.json() == []
        other_alerts = await client.get("/api/v1/security/alerts")
        assert other_alerts.json() == []


@pytest.mark.asyncio
async def test_rate_limit_check_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.post(
            "/api/v1/security/rate-limit-check", json={"key": "login", "limit": 5}
        )
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_rate_limit_check_allows_when_limiter_permits(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="sec-g")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/security/rate-limit-check", json={"key": "login", "limit": 5}
        )
        assert response.status_code == 204
