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


async def _submit_ticket(
    client: AsyncClient, *, priority: str = "normal", category: str = "generalInquiry"
) -> dict:
    response = await client.post(
        "/api/v1/support/tickets",
        json={
            "subject": "Cannot access my account",
            "category": category,
            "priority": priority,
            "message": "I am locked out.",
            "attachments": [],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_submit_ticket_sets_sla_and_first_message(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="sup-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            body = await _submit_ticket(client, priority="urgent")
    finally:
        app.dependency_overrides.clear()

    assert body["status"] == "open"
    assert body["requester_id"] == "sup-a"
    assert len(body["messages"]) == 1
    assert body["messages"][0]["is_agent"] is False
    # urgent = 30 min first-response SLA
    from datetime import datetime

    created = datetime.fromisoformat(body["created_at"])
    due = datetime.fromisoformat(body["first_response_due_at"])
    assert (due - created).total_seconds() == pytest.approx(30 * 60, abs=5)


@pytest.mark.asyncio
async def test_get_ticket_is_owner_or_staff_scoped(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="sup-b")
        ticket = await _submit_ticket(client)
        ticket_id = ticket["id"]

        own = await client.get(f"/api/v1/support/tickets/{ticket_id}")

        overrides(session, "applicant", uid="sup-c")
        other = await client.get(f"/api/v1/support/tickets/{ticket_id}")

        overrides(session, "supportOfficer")
        staff = await client.get(f"/api/v1/support/tickets/{ticket_id}")
    app.dependency_overrides.clear()

    assert own.status_code == 200
    assert other.status_code == 404
    assert staff.status_code == 200


@pytest.mark.asyncio
async def test_agent_queue_requires_staff_and_excludes_closed(
    session: AsyncSession,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="sup-d")
        denied = await client.get("/api/v1/support/tickets/queue")
        assert denied.status_code == 403
        ticket = await _submit_ticket(client)

        overrides(session, "supportOfficer", uid="agent-1")
        queue_before = await client.get("/api/v1/support/tickets/queue")
        # GET .../queue autobegins a read transaction on the shared session
        # that nothing commits; close it before the next call opens its own
        # session.begin(), same pattern as test_providers_route.py.
        await session.commit()
        await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/status",
            json={"status": "resolved", "notes": "Fixed."},
        )
        queue_after = await client.get("/api/v1/support/tickets/queue")
    app.dependency_overrides.clear()

    assert len(queue_before.json()) == 1
    assert len(queue_after.json()) == 0


@pytest.mark.asyncio
async def test_assign_self_assigns_caller(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="sup-e")
        ticket = await _submit_ticket(client)

        overrides(session, "supportOfficer", uid="agent-2")
        assigned = await client.post(f"/api/v1/support/tickets/{ticket['id']}/assign")
    app.dependency_overrides.clear()

    assert assigned.status_code == 200
    body = assigned.json()
    assert body["assigned_agent_id"] == "agent-2"
    assert body["status"] == "assigned"


@pytest.mark.asyncio
async def test_add_message_sets_is_agent_from_role_not_client(
    session: AsyncSession,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="sup-f")
        ticket = await _submit_ticket(client)

        overrides(session, "supportOfficer")
        agent_reply = await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/messages",
            json={"message": "Looking into it.", "attachments": []},
        )

        overrides(session, "applicant", uid="sup-f")
        applicant_reply = await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/messages",
            json={"message": "Thanks!", "attachments": []},
        )

        overrides(session, "applicant", uid="sup-g")
        denied = await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/messages",
            json={"message": "Not my ticket.", "attachments": []},
        )
    app.dependency_overrides.clear()

    assert agent_reply.status_code == 200
    assert agent_reply.json()["messages"][-1]["is_agent"] is True
    assert agent_reply.json()["status"] == "waitingForUser"
    assert applicant_reply.status_code == 200
    assert applicant_reply.json()["messages"][-1]["is_agent"] is False
    assert applicant_reply.json()["status"] == "inProgress"
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_internal_note_requires_staff_and_hidden_from_requester(
    session: AsyncSession,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="sup-h")
        ticket = await _submit_ticket(client)

        denied = await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/notes",
            json={"note": "internal"},
        )

        overrides(session, "supportOfficer", uid="agent-3")
        added = await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/notes",
            json={"note": "Escalation candidate."},
        )
    app.dependency_overrides.clear()

    assert denied.status_code == 403
    assert added.status_code == 200
    assert added.json()["internal_notes"][0]["agent_id"] == "agent-3"


@pytest.mark.asyncio
async def test_reopen_requires_closed_or_resolved(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="sup-i")
        ticket = await _submit_ticket(client)

        overrides(session, "supportOfficer")
        too_early = await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/status",
            json={"status": "reopened", "notes": ""},
        )
        await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/status",
            json={"status": "resolved", "notes": "done"},
        )
        reopened = await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/status",
            json={"status": "reopened", "notes": "not fixed"},
        )
    app.dependency_overrides.clear()

    assert too_early.status_code == 409
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "reopened"


@pytest.mark.asyncio
async def test_survey_only_by_requester_after_resolution(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="sup-j")
        ticket = await _submit_ticket(client)

        too_early = await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/survey",
            json={"rating": 5, "comment": "great"},
        )

        overrides(session, "supportOfficer")
        await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/status",
            json={"status": "resolved", "notes": "done"},
        )

        overrides(session, "applicant", uid="sup-k")
        wrong_user = await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/survey",
            json={"rating": 3},
        )

        overrides(session, "applicant", uid="sup-j")
        ok = await client.post(
            f"/api/v1/support/tickets/{ticket['id']}/survey",
            json={"rating": 5, "comment": "great"},
        )
    app.dependency_overrides.clear()

    assert too_early.status_code == 409
    assert wrong_user.status_code == 409
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_knowledge_search_only_returns_published(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "supportOfficer")
        await client.put(
            "/api/v1/support/knowledge/kb-1",
            json={
                "title": "Password reset",
                "summary": "How to reset your password",
                "content": "Go to settings...",
                "type": "article",
                "category": "accountAccess",
                "language_code": "en",
                "published": True,
                "keywords": ["password", "reset"],
            },
        )
        await client.put(
            "/api/v1/support/knowledge/kb-2",
            json={
                "title": "Draft article",
                "summary": "Not ready",
                "content": "WIP",
                "type": "article",
                "category": "accountAccess",
                "language_code": "en",
                "published": False,
                "keywords": [],
            },
        )

        overrides(session, "applicant", uid="sup-l")
        results = await client.get("/api/v1/support/knowledge", params={"query": "password"})
        no_match = await client.get("/api/v1/support/knowledge", params={"query": "unrelated"})
    app.dependency_overrides.clear()

    assert len(results.json()) == 1
    assert results.json()[0]["id"] == "kb-1"
    assert no_match.json() == []


@pytest.mark.asyncio
async def test_save_article_and_template_require_staff(session: AsyncSession) -> None:
    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            article_denied = await client.put(
                "/api/v1/support/knowledge/kb-3",
                json={
                    "title": "x",
                    "summary": "x",
                    "content": "x",
                    "type": "article",
                    "category": "accountAccess",
                    "published": False,
                    "keywords": [],
                },
            )
            template_denied = await client.put(
                "/api/v1/support/templates/tpl-1",
                json={
                    "name": "x",
                    "category": "accountAccess",
                    "subject": "x",
                    "body": "x",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert article_denied.status_code == 403
    assert template_denied.status_code == 403


@pytest.mark.asyncio
async def test_performance_report_requires_staff(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="sup-m")
        denied = await client.get("/api/v1/support/performance-report")
        await _submit_ticket(client)

        overrides(session, "administrator")
        report = await client.get("/api/v1/support/performance-report")
    app.dependency_overrides.clear()

    assert denied.status_code == 403
    assert report.status_code == 200
    assert report.json()["total_tickets"] == 1


@pytest.mark.asyncio
async def test_attachment_size_and_executable_validation(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="sup-n")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            too_big = await client.post(
                "/api/v1/support/tickets",
                json={
                    "subject": "s",
                    "category": "generalInquiry",
                    "priority": "low",
                    "message": "m",
                    "attachments": [
                        {
                            "id": "a1",
                            "name": "big.pdf",
                            "storage_location": "support-attachments/sup-n/big.pdf",
                            "content_type": "application/pdf",
                            "size_bytes": 11 * 1024 * 1024,
                        }
                    ],
                },
            )
            executable = await client.post(
                "/api/v1/support/tickets",
                json={
                    "subject": "s",
                    "category": "generalInquiry",
                    "priority": "low",
                    "message": "m",
                    "attachments": [
                        {
                            "id": "a2",
                            "name": "bad.exe",
                            "storage_location": "support-attachments/sup-n/bad.exe",
                            "content_type": "application/x-msdownload",
                            "size_bytes": 100,
                        }
                    ],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert too_big.status_code == 422
    assert executable.status_code == 422


@pytest.mark.asyncio
async def test_support_requires_authentication(session: AsyncSession) -> None:
    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = database
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/support/tickets/mine")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
