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
from app.models.audit_log import AuditAction, AuditResult
from app.services.audit_log import append_audit_record


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
async def test_records_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/audit/records")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_records_requires_administrator_role(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/audit/records")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_search_filters_and_masks_pii(session: AsyncSession) -> None:
    async with session.begin():
        await append_audit_record(
            session,
            actor_id="user-1",
            actor_role="administrator",
            action=AuditAction.profileChanged,
            entity_type="profile",
            entity_id="user-1",
            result=AuditResult.success,
            correlation_id="corr-1",
            previous_value="email=old@example.test",
            new_value="email=new@example.test, password=hunter2secret",
            ip_address="203.0.113.7",
        )
        await append_audit_record(
            session,
            actor_id="user-2",
            actor_role="applicant",
            action=AuditAction.login,
            entity_type="session",
            entity_id="user-2",
            result=AuditResult.failure,
            correlation_id="corr-2",
        )
    await session.commit()

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        all_records = await client.get("/api/v1/audit/records")
        assert len(all_records.json()) == 2

        filtered = await client.get(
            "/api/v1/audit/records", params={"actor_id": "user-1"}
        )
        assert len(filtered.json()) == 1
        record = filtered.json()[0]
        assert "hunter2secret" not in record["new_value"]
        assert "password=***" in record["new_value"]
        assert "[masked-email]" in record["new_value"]
        assert record["ip_address"] == "203.0.*.*"

        by_action = await client.get(
            "/api/v1/audit/records", params={"action": "login"}
        )
        assert len(by_action.json()) == 1
        assert by_action.json()[0]["actor_id"] == "user-2"


@pytest.mark.asyncio
async def test_export_returns_csv(session: AsyncSession) -> None:
    async with session.begin():
        await append_audit_record(
            session,
            actor_id="user-3",
            actor_role="administrator",
            action=AuditAction.administrativeAction,
            entity_type="config",
            entity_id="global",
            result=AuditResult.success,
            correlation_id="corr-3",
        )
    await session.commit()

    overrides(session, "securityAdministrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        export = await client.get("/api/v1/audit/records/export")
        assert export.status_code == 200
        csv = export.json()["csv"]
        assert "audit_id,actor_id" in csv
        assert "user-3" in csv


@pytest.mark.asyncio
async def test_integrity_detects_tampering(session: AsyncSession) -> None:
    async with session.begin():
        await append_audit_record(
            session,
            actor_id="user-4",
            actor_role="administrator",
            action=AuditAction.securityEvent,
            entity_type="alert",
            entity_id="alert-1",
            result=AuditResult.success,
            correlation_id="corr-4",
        )
    await session.commit()

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        intact = await client.get("/api/v1/audit/integrity")
        assert intact.json() is True

    from sqlalchemy import select

    from app.models.audit_log import AuditRecord

    record = await session.scalar(select(AuditRecord))
    record.entity_id = "tampered"
    await session.commit()

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        tampered = await client.get("/api/v1/audit/integrity")
        assert tampered.json() is False


@pytest.mark.asyncio
async def test_retention_policy_round_trip_and_minimum(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        defaults = await client.get("/api/v1/audit/retention-policy")
        assert defaults.json()["retention_days"] == 2555
        await session.commit()

        rejected = await client.put(
            "/api/v1/audit/retention-policy", json={"retention_days": 30}
        )
        assert rejected.status_code == 422
        await session.commit()

        saved = await client.put(
            "/api/v1/audit/retention-policy", json={"retention_days": 400}
        )
        assert saved.status_code == 200
        assert saved.json()["retention_days"] == 400


@pytest.mark.asyncio
async def test_enforce_retention_removes_expired_and_keeps_chain_continuous(
    session: AsyncSession,
) -> None:
    from datetime import timedelta

    from app.services.parsing import utc_now

    async with session.begin():
        await append_audit_record(
            session,
            actor_id="user-5",
            actor_role="administrator",
            action=AuditAction.apiRequest,
            entity_type="request",
            entity_id="req-1",
            result=AuditResult.success,
            correlation_id="corr-5",
        )

    from sqlalchemy import select

    from app.models.audit_log import AuditRecord

    old_record = await session.scalar(select(AuditRecord))
    old_record.timestamp = utc_now() - timedelta(days=3000)
    await session.commit()

    async with session.begin():
        await append_audit_record(
            session,
            actor_id="user-6",
            actor_role="administrator",
            action=AuditAction.apiRequest,
            entity_type="request",
            entity_id="req-2",
            result=AuditResult.success,
            correlation_id="corr-6",
        )
    await session.commit()

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        enforced = await client.post("/api/v1/audit/retention/enforce")
        assert enforced.status_code == 200
        assert enforced.json()["removed"] == 1
        await session.commit()

        intact = await client.get("/api/v1/audit/integrity")
        assert intact.json() is True


@pytest.mark.asyncio
async def test_import_records_requires_audit_access(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/audit/import-records")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_import_records_readable_by_security_administrator(
    session: AsyncSession,
) -> None:
    """The gap this route closes: a Security Administrator previously had

    no way to read ImportAuditLog (the pipeline covering opportunity
    verification and provider lifecycle actions) even though the role
    already had read access to the separate AuditRecord trail.
    """
    from app.models import ImportAuditLog

    async with session.begin():
        session.add(
            ImportAuditLog(
                actor_id="officer-1",
                actor_role="verificationOfficer",
                action="verification_approved",
                entity_type="external_opportunity",
                entity_id="00000000-0000-0000-0000-000000000001",
                result="success",
                correlation_id="corr-import-1",
            )
        )
        session.add(
            ImportAuditLog(
                actor_id="owner-1",
                actor_role="opportunityProvider",
                action="provider_registered",
                entity_type="provider",
                entity_id="00000000-0000-0000-0000-000000000002",
                result="success",
                correlation_id="corr-import-2",
            )
        )

    overrides(session, "securityAdministrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/audit/import-records")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    actions = {item["action"] for item in body["items"]}
    assert actions == {"verification_approved", "provider_registered"}


@pytest.mark.asyncio
async def test_import_records_filter_by_actor_and_paginate(session: AsyncSession) -> None:
    from app.models import ImportAuditLog

    async with session.begin():
        for index in range(3):
            session.add(
                ImportAuditLog(
                    actor_id="officer-1" if index < 2 else "officer-2",
                    actor_role="verificationOfficer",
                    action="verification_approved",
                    entity_type="external_opportunity",
                    entity_id=f"00000000-0000-0000-0000-00000000000{index}",
                    result="success",
                    correlation_id=f"corr-{index}",
                )
            )

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        filtered = await client.get(
            "/api/v1/audit/import-records", params={"actor_id": "officer-1"}
        )
        paged = await client.get(
            "/api/v1/audit/import-records", params={"page": 1, "page_size": 2}
        )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 2
    assert paged.status_code == 200
    assert paged.json()["total"] == 3
    assert len(paged.json()["items"]) == 2
