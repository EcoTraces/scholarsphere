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
async def test_rules_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/data-lifecycle/rules")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_rules_requires_administrator(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/data-lifecycle/rules")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_rule_rejects_short_retention(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.put(
            "/api/v1/data-lifecycle/rules/auditLog",
            json={
                "active_duration_seconds": 86400,
                "archive_duration_seconds": 86400,
                "delete_from_backups_after_seconds": 86400,
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_save_rule_and_list(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        saved = await client.put(
            "/api/v1/data-lifecycle/rules/document",
            json={
                "active_duration_seconds": 86400 * 30,
                "archive_duration_seconds": 86400 * 60,
                "delete_from_backups_after_seconds": 86400 * 35,
            },
        )
        assert saved.status_code == 200, saved.text
        await session.commit()

        rules = await client.get("/api/v1/data-lifecycle/rules")
        assert len(rules.json()) == 1
        assert rules.json()[0]["entity_type"] == "document"


@pytest.mark.asyncio
async def test_register_softdelete_permanentlydelete_and_verify(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator", uid="lifecycle-admin")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        registered = await client.post(
            "/api/v1/data-lifecycle/records",
            json={"entity_type": "document", "entity_id": "doc-1", "owner_id": "user-1"},
        )
        assert registered.status_code == 200, registered.text
        assert registered.json()["status"] == "active"
        await session.commit()

        soft_deleted = await client.post(
            "/api/v1/data-lifecycle/records/document/doc-1/soft-delete"
        )
        assert soft_deleted.status_code == 200
        assert soft_deleted.json()["status"] == "softDeleted"
        await session.commit()

        not_yet = await client.get(
            "/api/v1/data-lifecycle/records/document/doc-1/verify-deletion"
        )
        assert not_yet.json() is False
        await session.commit()

        permanently = await client.post(
            "/api/v1/data-lifecycle/records/document/doc-1/permanently-delete"
        )
        assert permanently.status_code == 200
        assert permanently.json()["status"] == "permanentlyDeleted"
        assert permanently.json()["deletion_verification"] is not None
        await session.commit()

        verified = await client.get(
            "/api/v1/data-lifecycle/records/document/doc-1/verify-deletion"
        )
        assert verified.json() is True
        await session.commit()

        cannot_restore = await client.post(
            "/api/v1/data-lifecycle/records/document/doc-1/restore"
        )
        assert cannot_restore.status_code == 409


@pytest.mark.asyncio
async def test_legal_hold_blocks_deletion(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/api/v1/data-lifecycle/records",
            json={"entity_type": "document", "entity_id": "doc-2"},
        )
        await session.commit()

        hold = await client.post(
            "/api/v1/data-lifecycle/legal-holds/document/doc-2",
            json={"reason": "Litigation hold"},
        )
        assert hold.status_code == 200, hold.text
        await session.commit()

        blocked = await client.post(
            "/api/v1/data-lifecycle/records/document/doc-2/soft-delete"
        )
        assert blocked.status_code == 409


@pytest.mark.asyncio
async def test_cleanup_archives_and_deletes_respecting_holds(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.put(
            "/api/v1/data-lifecycle/rules/document",
            json={
                "active_duration_seconds": 0,
                "archive_duration_seconds": 0,
                "delete_from_backups_after_seconds": 86400,
            },
        )
        await session.commit()

        await client.post(
            "/api/v1/data-lifecycle/records",
            json={"entity_type": "document", "entity_id": "doc-3"},
        )
        await session.commit()
        await client.post(
            "/api/v1/data-lifecycle/records",
            json={"entity_type": "document", "entity_id": "doc-4"},
        )
        await session.commit()
        await client.post(
            "/api/v1/data-lifecycle/legal-holds/document/doc-4",
            json={"reason": "Hold"},
        )
        await session.commit()

        report = await client.post("/api/v1/data-lifecycle/cleanup")
        assert report.status_code == 200, report.text
        body = report.json()
        assert body["archived"] == 1
        assert body["skipped_legal_holds"] == 1
