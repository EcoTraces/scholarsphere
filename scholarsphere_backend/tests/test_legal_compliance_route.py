from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

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
from app.models.legal_compliance import LegalPolicy, LegalPolicyType
from app.services.legal_policy_seed import seed_default_legal_policies


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


async def _publish(
    client: AsyncClient,
    *,
    policy_id: str,
    version: str,
    material_change: bool = False,
    requires_acceptance: bool = True,
) -> dict:
    response = await client.post(
        "/api/v1/legal/policies",
        json={
            "id": policy_id,
            "type": "termsAndConditions",
            "version": version,
            "title": "Terms and Conditions",
            "content": "Full legal text.",
            "effective_at": datetime.now(timezone.utc).isoformat(),
            "requires_acceptance": requires_acceptance,
            "material_change": material_change,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_current_policy_is_public(session: AsyncSession) -> None:
    # Deliberately the one legal-compliance endpoint with no auth
    # requirement: a visitor must be able to read Terms & Conditions /
    # Privacy Policy from the public footer before ever signing in, not
    # only after creating an account.
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/legal/policies/termsAndConditions/current")
        assert response.status_code == 200
        assert response.json() is None


@pytest.mark.asyncio
async def test_versions_still_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/legal/policies/termsAndConditions/versions")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_publish_requires_staff_and_rejects_duplicate_version(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        forbidden = await client.post(
            "/api/v1/legal/policies",
            json={
                "id": "tc-1",
                "type": "termsAndConditions",
                "version": "1.0",
                "title": "Terms",
                "content": "Text",
                "effective_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert forbidden.status_code == 403

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _publish(client, policy_id="tc-1", version="1.0")
        await session.commit()
        collision = await client.post(
            "/api/v1/legal/policies",
            json={
                "id": "tc-1-dup",
                "type": "termsAndConditions",
                "version": "1.0",
                "title": "Terms",
                "content": "Text",
                "effective_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert collision.status_code == 409


@pytest.mark.asyncio
async def test_current_returns_latest_published_version(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _publish(client, policy_id="tc-1", version="1.0")
        await session.commit()
        await _publish(client, policy_id="tc-2", version="2.0")
        await session.commit()

        current = await client.get("/api/v1/legal/policies/termsAndConditions/current")
        assert current.json()["version"] == "2.0"

        versions = await client.get("/api/v1/legal/policies/termsAndConditions/versions")
        assert [item["version"] for item in versions.json()] == ["1.0", "2.0"]


@pytest.mark.asyncio
async def test_accept_requires_current_version(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _publish(client, policy_id="tc-1", version="1.0")
        await session.commit()
        await _publish(client, policy_id="tc-2", version="2.0")
        await session.commit()

    overrides(session, "applicant", uid="legal-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        stale = await client.post(
            "/api/v1/legal/acceptances",
            json={"policy_id": "tc-1", "policy_version": "1.0", "ip_address": "127.0.0.1"},
        )
        assert stale.status_code == 409

        current = await client.post(
            "/api/v1/legal/acceptances",
            json={"policy_id": "tc-2", "policy_version": "2.0", "ip_address": "127.0.0.1"},
        )
        assert current.status_code == 204
        await session.commit()

        accepted = await client.get("/api/v1/legal/policies/termsAndConditions/accepted")
        assert accepted.json() is True


@pytest.mark.asyncio
async def test_accept_is_upsert_by_user_and_policy(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _publish(client, policy_id="tc-1", version="1.0")
        await session.commit()

    overrides(session, "applicant", uid="legal-b")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.post(
            "/api/v1/legal/acceptances",
            json={"policy_id": "tc-1", "policy_version": "1.0", "ip_address": "1.1.1.1"},
        )
        assert first.status_code == 204
        await session.commit()
        second = await client.post(
            "/api/v1/legal/acceptances",
            json={"policy_id": "tc-1", "policy_version": "1.0", "ip_address": "2.2.2.2"},
        )
        assert second.status_code == 204


@pytest.mark.asyncio
async def test_pending_notifications_only_for_unaccepted_material_changes(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _publish(client, policy_id="tc-1", version="1.0", material_change=True)
        await session.commit()

    overrides(session, "applicant", uid="legal-c")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        pending_before = await client.get("/api/v1/legal/pending-notifications")
        assert len(pending_before.json()) == 1
        await session.commit()

        await client.post(
            "/api/v1/legal/acceptances",
            json={"policy_id": "tc-1", "policy_version": "1.0", "ip_address": ""},
        )
        await session.commit()

        pending_after = await client.get("/api/v1/legal/pending-notifications")
        assert pending_after.json() == []


@pytest.mark.asyncio
async def test_legal_requests_require_staff(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        forbidden = await client.post(
            "/api/v1/legal/requests",
            json={
                "id": "req-1",
                "type": "takedown",
                "requester": "Acme Corp",
                "description": "Remove infringing listing.",
            },
        )
        assert forbidden.status_code == 403

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        allowed = await client.post(
            "/api/v1/legal/requests",
            json={
                "id": "req-1",
                "type": "takedown",
                "requester": "Acme Corp",
                "description": "Remove infringing listing.",
            },
        )
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()["status"] == "submitted"
        await session.commit()

        listed = await client.get("/api/v1/legal/requests")
        assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_seed_default_legal_policies_is_idempotent(session: AsyncSession) -> None:
    await seed_default_legal_policies(session)
    await session.commit()

    seeded = (await session.scalars(select(LegalPolicy))).all()
    seeded_types = {policy.type for policy in seeded}
    assert seeded_types == {
        LegalPolicyType.terms_and_conditions,
        LegalPolicyType.privacy_policy,
        LegalPolicyType.cookie_policy,
    }
    assert all(policy.content.strip() for policy in seeded)

    # Re-running never overwrites/duplicates - matches
    # seed_default_plan's "seed, not sync" contract.
    await seed_default_legal_policies(session)
    await session.commit()
    again = (await session.scalars(select(LegalPolicy))).all()
    assert len(again) == len(seeded)


@pytest.mark.asyncio
async def test_compliance_records_upsert_and_require_staff(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        forbidden = await client.put(
            "/api/v1/legal/compliance/rec-1",
            json={
                "framework": "GDPR",
                "obligation": "Respond to data subject requests within 30 days.",
                "status": "onTrack",
                "owner": "compliance-team",
                "review_due_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            },
        )
        assert forbidden.status_code == 403

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.put(
            "/api/v1/legal/compliance/rec-1",
            json={
                "framework": "GDPR",
                "obligation": "Respond to data subject requests within 30 days.",
                "status": "onTrack",
                "owner": "compliance-team",
                "review_due_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            },
        )
        assert created.status_code == 200, created.text
        await session.commit()

        updated = await client.put(
            "/api/v1/legal/compliance/rec-1",
            json={
                "framework": "GDPR",
                "obligation": "Respond to data subject requests within 30 days.",
                "status": "atRisk",
                "owner": "compliance-team",
                "review_due_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            },
        )
        assert updated.json()["status"] == "atRisk"
        await session.commit()

        records = await client.get("/api/v1/legal/compliance")
        assert len(records.json()) == 1
