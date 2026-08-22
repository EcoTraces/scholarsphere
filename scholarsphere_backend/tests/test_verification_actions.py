import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import ExternalOpportunity, ImportAuditLog, VerificationHistory
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.opportunity_import import import_opportunities
from app.services.source_registry import seed_opportunity_sources


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
        async with database_session.begin():
            await seed_opportunity_sources(database_session)
        yield database_session
    await engine.dispose()


def user(role: str) -> AuthenticatedUser:
    return AuthenticatedUser(
        uid=f"{role}-user",
        email=f"{role}@example.test",
        email_verified=True,
        role=role,
        permissions=frozenset(),
    )


def overrides(session: AsyncSession, role: str) -> None:
    async def current_user() -> AuthenticatedUser:
        return user(role)

    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


async def _import_one(session: AsyncSession, *, external_id: str = "action-grant-1") -> str:
    record = NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id=external_id,
        title="Community Resilience Grant",
        opportunity_type="grant",
        provider_name="Department of Resilience",
        country="United States",
        deadline=date.today() + timedelta(days=30),
        opportunity_status="posted",
        official_source_url="https://example.test/action-grant-1",
        official_application_url="https://example.test/action-grant-1/apply",
        raw_payload={"id": external_id},
    )
    await import_opportunities(session, [record], source_code="grants_gov", actor_id="officer-1")
    opportunity = await session.scalar(
        select(ExternalOpportunity).where(ExternalOpportunity.external_id == external_id)
    )
    opportunity_id = str(opportunity.id)
    await session.commit()
    return opportunity_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [
        ("reverification_required", "reverification_required"),
        ("expired", "expired"),
        ("source_unavailable", "source_unavailable"),
        ("suspicious", "suspicious"),
    ],
)
async def test_new_decision_values_transition_status_without_full_checklist(
    session: AsyncSession, decision: str, expected_status: str
) -> None:
    opportunity_id = await _import_one(session)
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}/verification",
                json={"decision": decision, "notes": "Reviewed against the official source."},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["verification_status"] == expected_status
    assert body["publication_status"] == "unpublished"
    actions = set((await session.scalars(select(ImportAuditLog.action))).all())
    assert f"verification_{decision}" in actions


@pytest.mark.asyncio
async def test_approval_still_requires_full_checklist(session: AsyncSession) -> None:
    opportunity_id = await _import_one(session)
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}/verification",
                json={
                    "decision": "approved",
                    "notes": "Missing one check.",
                    "source_checked": True,
                    "application_link_checked": True,
                    "deadline_checked": True,
                    "duplicate_checked": False,
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_applicant_and_unauthenticated_are_denied_on_all_new_endpoints(
    session: AsyncSession,
) -> None:
    opportunity_id = await _import_one(session)
    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            review = await client.get(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}/review"
            )
            note = await client.post(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}/notes",
                json={"note": "Trying to add a note."},
            )
            edit = await client.patch(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}",
                json={"reason": "Trying to edit.", "title": "New title"},
            )
    finally:
        app.dependency_overrides.clear()
    assert review.status_code == 403
    assert note.status_code == 403
    assert edit.status_code == 403

    unauthenticated = TestClient(app).get(
        f"/api/v1/external-opportunities/opportunities/{opportunity_id}/review"
    )
    assert unauthenticated.status_code == 401


@pytest.mark.asyncio
async def test_get_review_reflects_decision(session: AsyncSession) -> None:
    opportunity_id = await _import_one(session)
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            missing = await client.get(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}/review"
            )
            # This GET reads without wrapping in session.begin() (matching the
            # rest of the read-only endpoints), which autobegins a transaction
            # on this test's shared session. Commit it before the next request
            # opens its own session.begin(), mirroring the existing pattern in
            # test_public_opportunities_route.py::test_full_pipeline_....
            await session.commit()
            await client.post(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}/verification",
                json={"decision": "suspicious", "notes": "Looks off."},
            )
            after = await client.get(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}/review"
            )
    finally:
        app.dependency_overrides.clear()
    # A VerificationReview row is created at import time, so it exists even
    # before any decision has been made - only its `decision` field changes.
    assert missing.status_code == 200
    assert missing.json()["decision"] == "pending"
    assert after.status_code == 200
    assert after.json()["decision"] == "suspicious"
    assert after.json()["notes"] == "Looks off."
    assert after.json()["verification_officer_id"] == "verificationOfficer-user"


@pytest.mark.asyncio
async def test_note_is_appended_without_changing_status(session: AsyncSession) -> None:
    opportunity_id = await _import_one(session)
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}/notes",
                json={"note": "Called the program office to confirm the deadline."},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["verification_status"] == "pending"
    history = (
        await session.scalars(
            select(VerificationHistory).where(
                VerificationHistory.opportunity_id == uuid.UUID(opportunity_id)
            )
        )
    ).all()
    assert len(history) == 1
    assert history[0].previous_status == history[0].new_status == "pending"
    assert history[0].reason == "Called the program office to confirm the deadline."
    actions = set((await session.scalars(select(ImportAuditLog.action))).all())
    assert "verification_note_added" in actions


@pytest.mark.asyncio
async def test_edit_diffs_fields_and_requires_reason(session: AsyncSession) -> None:
    opportunity_id = await _import_one(session)
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            missing_reason = await client.patch(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}",
                json={"title": "Corrected Title"},
            )
            no_changes = await client.patch(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}",
                json={"reason": "No actual change."},
            )
            edit = await client.patch(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}",
                json={
                    "reason": "Official source corrected the award ceiling and title.",
                    "title": "Community Resilience Grant (Corrected)",
                    "award_ceiling": 50000,
                },
            )
            insecure_url = await client.patch(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}",
                json={
                    "reason": "Testing insecure URL rejection.",
                    "official_source_url": "http://insecure.example.test",
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert missing_reason.status_code == 422
    assert no_changes.status_code == 400
    assert edit.status_code == 200
    body = edit.json()
    assert set(body["changed_fields"]) == {"title", "award_ceiling"}
    assert insecure_url.status_code == 422

    opportunity = await session.get(ExternalOpportunity, uuid.UUID(opportunity_id))
    assert opportunity.title == "Community Resilience Grant (Corrected)"
    assert opportunity.award_ceiling == 50000

    history = (
        await session.scalars(
            select(VerificationHistory).where(
                VerificationHistory.opportunity_id == uuid.UUID(opportunity_id)
            )
        )
    ).all()
    edit_entries = [entry for entry in history if "title" in (entry.changed_fields or {})]
    assert len(edit_entries) == 1
    assert edit_entries[0].changed_fields["title"]["previous"] == "Community Resilience Grant"
    assert edit_entries[0].changed_fields["title"]["new"] == "Community Resilience Grant (Corrected)"
    actions = set((await session.scalars(select(ImportAuditLog.action))).all())
    assert "opportunity_edited" in actions


@pytest.mark.asyncio
async def test_edit_sanitizes_description_html_like_source_import_does(
    session: AsyncSession,
) -> None:
    opportunity_id = await _import_one(session)
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            edit = await client.patch(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}",
                json={
                    "reason": "Adding a corrected description from the source page.",
                    "description": (
                        '<p onclick="steal()">Applications open in spring.</p>'
                        "<script>steal()</script>"
                    ),
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert edit.status_code == 200
    assert edit.json()["changed_fields"] == ["description"]

    opportunity = await session.get(ExternalOpportunity, uuid.UUID(opportunity_id))
    assert opportunity.description is not None
    assert "onclick" not in opportunity.description
    assert "script" not in opportunity.description.lower()
    assert "steal" not in opportunity.description
    assert "Applications open in spring." in opportunity.description


@pytest.mark.asyncio
async def test_officer_evidence_endpoint_works_before_publication(
    session: AsyncSession,
) -> None:
    opportunity_id = await _import_one(session)
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            officer_evidence = await client.get(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}/evidence"
            )
            # The applicant-facing evidence endpoint must still 404 for a
            # pending, unpublished opportunity.
            public_evidence = await client.get(
                f"/api/v1/opportunities/{opportunity_id}/evidence"
            )
    finally:
        app.dependency_overrides.clear()
    assert officer_evidence.status_code == 200
    assert officer_evidence.json()["source_code"] == "grants_gov"
    assert public_evidence.status_code == 404


@pytest.mark.asyncio
async def test_pending_verification_list_includes_full_review_fields(
    session: AsyncSession,
) -> None:
    await _import_one(session)
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/external-opportunities/pending-verification"
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["official_source_url"] == "https://example.test/action-grant-1"
    assert item["official_application_url"] == "https://example.test/action-grant-1/apply"
    assert item["opportunity_type"] == "grant"
    assert item["country"] == "United States"


def _overrides_as(session: AsyncSession, uid: str, role: str) -> None:
    """Like overrides(), but with a caller-chosen uid instead of the shared

    f"{role}-user" default - needed to test that per-officer counts are
    genuinely scoped to the calling officer, not just to their role.
    """

    async def current_user() -> AuthenticatedUser:
        return AuthenticatedUser(
            uid=uid, email=f"{uid}@example.test", email_verified=True, role=role,
            permissions=frozenset(),
        )

    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


async def _decide(
    client: AsyncClient, opportunity_id: str, decision: str, **checks: bool
) -> None:
    response = await client.post(
        f"/api/v1/external-opportunities/opportunities/{opportunity_id}/verification",
        json={"decision": decision, "notes": "Reviewed.", **checks},
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_verification_summary_reports_real_pending_count(
    session: AsyncSession,
) -> None:
    await _import_one(session, external_id="summary-pending-1")
    await _import_one(session, external_id="summary-pending-2")
    overrides(session, "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/external-opportunities/verification-summary"
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["pending"] == 2
    assert body["by_status"]["pending"] == 2
    assert body["verified_today"] == 0
    assert body["approved_by_you"] == 0
    assert len(body["decisions_last_7_days"]) == 7
    # Every seeded source in this suite is "official" trust level - a real,
    # honest fact, not a fabricated 100%.
    assert body["official_source_ratio"] == 1.0


@pytest.mark.asyncio
async def test_verification_summary_counts_todays_approval_and_attributes_it(
    session: AsyncSession,
) -> None:
    opportunity_id = await _import_one(session, external_id="summary-approved-1")
    _overrides_as(session, "officer-alpha", "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await _decide(
                client,
                opportunity_id,
                "approved",
                source_checked=True,
                application_link_checked=True,
                deadline_checked=True,
                duplicate_checked=True,
            )
            response = await client.get(
                "/api/v1/external-opportunities/verification-summary"
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["pending"] == 0
    assert body["verified_today"] == 1
    assert body["approved_by_you"] == 1
    assert body["by_status"]["verified"] == 1
    assert body["decisions_last_7_days"][-1]["decisions"] == 1


@pytest.mark.asyncio
async def test_verification_summary_approved_by_you_is_scoped_per_officer(
    session: AsyncSession,
) -> None:
    opportunity_id = await _import_one(session, external_id="summary-approved-2")
    _overrides_as(session, "officer-alpha", "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await _decide(
                client,
                opportunity_id,
                "approved",
                source_checked=True,
                application_link_checked=True,
                deadline_checked=True,
                duplicate_checked=True,
            )
    finally:
        app.dependency_overrides.clear()

    # A *different* officer should see the same global counts (verified
    # today, by-status) but not be credited with an approval they didn't
    # make.
    _overrides_as(session, "officer-beta", "verificationOfficer")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/external-opportunities/verification-summary"
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["verified_today"] == 1
    assert body["approved_by_you"] == 0


@pytest.mark.asyncio
async def test_verification_summary_denied_for_applicant(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/external-opportunities/verification-summary"
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
