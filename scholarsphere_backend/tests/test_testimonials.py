from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthenticatedUser, get_current_user, permissions_for_role
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.testimonial import TestimonialDisplayMode as _DisplayMode
from app.schemas.testimonial import display_name_for


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
        # Real production tokens derive permissions from role via
        # permissions_for_role (app/core/auth.py) - matching that here is
        # what makes require_permissions("moderateContent") in
        # app/api/routes/testimonials.py actually pass for a "moderator"
        # the same way it would for a real signed-in moderator.
        permissions=permissions_for_role(role),
    )


def overrides(session: AsyncSession, role: str, uid: str | None = None) -> None:
    async def current_user() -> AuthenticatedUser:
        return user(role, uid)

    async def database() -> AsyncIterator[AsyncSession]:
        # A read-only route (list/get) never opens an explicit
        # `session.begin()` block (matching this codebase's own
        # convention - see e.g. app/api/routes/applications.py's
        # list/get endpoints), so SQLAlchemy autobegins an implicit
        # transaction on its first query that nothing ever closes. In
        # production that's harmless (get_db() hands out a brand-new
        # Session per request), but this fixture deliberately reuses one
        # Session across many simulated requests for simplicity, so a
        # dangling autobegin here would make the *next* request's own
        # explicit `session.begin()` raise "a transaction is already
        # begun". Closing it out after every request keeps this fixture
        # a faithful stand-in for the real per-request session lifecycle.
        # The `finally` (not a bare statement after `yield`) matters: a
        # route that raises (e.g. every 404 in this file) re-throws that
        # exception into this generator at the `yield` point, skipping
        # any unprotected cleanup below it - exactly the same reason
        # app/db/session.py's real get_db() wraps its own yield in
        # try/except.
        try:
            yield session
        finally:
            if session.in_transaction():
                await session.rollback()

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


def _draft_payload(**overrides_: Any) -> dict[str, Any]:
    payload = {
        "opportunity": {
            "opportunity_name": "Commonwealth Scholarship",
            "opportunity_provider": "Commonwealth Scholarship Commission",
            "opportunity_type": "scholarship",
            "country": "Sierra Leone",
            "degree_level": "Masters",
            "field_of_study": "Public Health",
            "success_year": 2026,
            "outcome": "awarded",
        },
        "experience": {
            "challenge": "I had no idea where to find funded master's programmes.",
            "discovery_story": "Found it through the ScholarSphere discovery feed.",
            "preparation_story": "Used the CV builder and requirement checklist.",
            "scholarsphere_help": "The eligibility matching saved weeks of manual research.",
            "outcome_narrative": "I was awarded the scholarship and started in September.",
            "impact": "This changed the trajectory of my public health career.",
            "advice": "Start early and track every deadline.",
            "features_used": ["opportunity_discovery", "cv_builder"],
        },
        "profile": {
            "full_name": "Aminata Kamara",
            "university": "University of Sussex",
            "program": "MSc Public Health",
        },
        "privacy": {
            "display_mode": "first_name_last_initial",
            "show_university": True,
            "show_country": True,
            "show_program": True,
            "show_photo": False,
        },
        "evidence_storage_paths": [],
    }
    payload.update(overrides_)
    return payload


async def _create_draft(client: AsyncClient, **overrides_: Any) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/testimonials/me/draft", json=_draft_payload(**overrides_)
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _submit(client: AsyncClient, testimonial_id: str) -> Any:
    return await client.post(
        f"/api/v1/testimonials/me/{testimonial_id}/submit",
        json={"consent_confirmed": True},
    )


@pytest.mark.asyncio
async def test_display_name_privacy_modes() -> None:
    assert display_name_for("Aminata Kamara", _DisplayMode.full_name) == "Aminata Kamara"
    assert (
        display_name_for("Aminata Kamara", _DisplayMode.first_name_last_initial)
        == "Aminata K."
    )
    assert display_name_for("Aminata Kamara", _DisplayMode.anonymous) == "Anonymous Applicant"
    assert display_name_for("Aminata", _DisplayMode.first_name_last_initial) == "Aminata"


@pytest.mark.asyncio
async def test_create_and_update_draft(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="story-a")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await _create_draft(client)
            assert created["status"] == "draft"
            testimonial_id = created["id"]

            update = await client.put(
                f"/api/v1/testimonials/me/{testimonial_id}/draft",
                json=_draft_payload(profile={"full_name": "Aminata K. Kamara", "university": None, "program": None}),
            )
            assert update.status_code == 200, update.text
            assert update.json()["full_name"] == "Aminata K. Kamara"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_requires_consent(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="story-b")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await _create_draft(client)
            response = await client.post(
                f"/api/v1/testimonials/me/{created['id']}/submit",
                json={"consent_confirmed": False},
            )
            assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_requires_minimum_content(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="story-c")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await _create_draft(
                client,
                experience={
                    "challenge": None,
                    "discovery_story": None,
                    "preparation_story": None,
                    "scholarsphere_help": None,
                    "outcome_narrative": None,
                    "impact": None,
                    "advice": None,
                    "features_used": [],
                },
            )
            response = await _submit(client, created["id"])
            assert response.status_code == 422
            assert "missing_fields" in response.json()["error"]["message"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cannot_edit_or_act_on_someone_elses_draft(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="story-owner")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await _create_draft(client)
    testimonial_id = created["id"]

    overrides(session, "applicant", uid="someone-else")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            get_response = await client.get(f"/api/v1/testimonials/me/{testimonial_id}")
            assert get_response.status_code == 404

            put_response = await client.put(
                f"/api/v1/testimonials/me/{testimonial_id}/draft", json=_draft_payload()
            )
            assert put_response.status_code == 404

            submit_response = await _submit(client, testimonial_id)
            assert submit_response.status_code == 404

            withdraw_response = await client.post(
                f"/api/v1/testimonials/me/{testimonial_id}/withdraw"
            )
            assert withdraw_response.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_non_moderator_cannot_access_admin_endpoints(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="story-d")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/admin/testimonials")
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_public_list_never_shows_unapproved_stories(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="story-e")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await _create_draft(client)
        submitted = await _submit(client, created["id"])
        assert submitted.status_code == 200

    overrides(session, "applicant", uid="browsing-user")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            listing = await client.get("/api/v1/success-stories")
            assert listing.status_code == 200
            assert listing.json()["items"] == []

            detail = await client.get(f"/api/v1/success-stories/{created['slug']}")
            assert detail.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_full_journey_submit_review_approve_publish_withdraw(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="story-f")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await _create_draft(client)
        testimonial_id = created["id"]
        submitted = await _submit(client, testimonial_id)
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "submitted"

    overrides(session, "moderator", uid="mod-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        review = await client.post(f"/api/v1/admin/testimonials/{testimonial_id}/review")
        assert review.status_code == 200
        assert review.json()["status"] == "under_review"

        reject_empty = await client.post(
            f"/api/v1/admin/testimonials/{testimonial_id}/approve", json={"reason": ""}
        )
        assert reject_empty.status_code == 422  # min_length=1 on the reason/notes field

        approve = await client.post(
            f"/api/v1/admin/testimonials/{testimonial_id}/approve",
            json={"reason": "Clear, honest story with a real outcome."},
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"
        assert approve.json()["verification_status"] == "unverified"

        verify = await client.post(
            f"/api/v1/admin/testimonials/{testimonial_id}/verify",
            json={"verification_method": "Award letter reviewed", "notes": "Matches provider records."},
        )
        assert verify.status_code == 200
        assert verify.json()["verification_status"] == "verified"
        assert verify.json()["verified_by"] == "mod-1"

        feature = await client.post(f"/api/v1/admin/testimonials/{testimonial_id}/feature")
        assert feature.status_code == 200
        assert feature.json()["featured"] is True

        history = await client.get(f"/api/v1/admin/testimonials/{testimonial_id}/history")
        assert history.status_code == 200
        statuses = [item["new_status"] for item in history.json()]
        assert statuses == [
            "submitted",
            "under_review",
            "approved",
            "approved",
            "approved",
        ]

    overrides(session, "applicant", uid="browsing-user-2")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listing = await client.get("/api/v1/success-stories", params={"verified_only": True})
        assert listing.status_code == 200
        assert len(listing.json()["items"]) == 1
        summary = listing.json()["items"][0]
        assert summary["display_name"] == "Aminata K."
        assert "verified" in summary["badges"]
        assert "featured" in summary["badges"]

        detail = await client.get(f"/api/v1/success-stories/{created['slug']}")
        assert detail.status_code == 200
        assert detail.json()["view_count"] == 1

        react = await client.post(
            f"/api/v1/success-stories/{created['slug']}/react", json={"reaction_type": "inspiring"}
        )
        assert react.status_code == 200
        assert react.json()["inspiring_count"] == 1

        # Switching reaction type moves the count, doesn't add a second one.
        react_again = await client.post(
            f"/api/v1/success-stories/{created['slug']}/react", json={"reaction_type": "helpful"}
        )
        assert react_again.status_code == 200
        assert react_again.json()["helpful_count"] == 1
        assert react_again.json()["inspiring_count"] == 0

        remove = await client.request(
            "DELETE", f"/api/v1/success-stories/{created['slug']}/react"
        )
        assert remove.status_code == 200
        assert remove.json()["helpful_count"] == 0

    overrides(session, "applicant", uid="story-f")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        withdrawn = await client.post(f"/api/v1/testimonials/me/{testimonial_id}/withdraw")
        assert withdrawn.status_code == 200
        assert withdrawn.json()["status"] == "withdrawn"

    overrides(session, "applicant", uid="browsing-user-3")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        after_withdraw = await client.get(f"/api/v1/success-stories/{created['slug']}")
        assert after_withdraw.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reject_then_resubmit_after_changes_requested(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="story-g")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await _create_draft(client)
        await _submit(client, created["id"])

    overrides(session, "moderator", uid="admin-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        changes = await client.post(
            f"/api/v1/admin/testimonials/{created['id']}/request-changes",
            json={"reason": "Please clarify the outcome date."},
        )
        assert changes.status_code == 200
        assert changes.json()["status"] == "changes_requested"

    overrides(session, "applicant", uid="story-g")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        mine = await client.get(f"/api/v1/testimonials/me/{created['id']}")
        assert mine.json()["rejection_reason"] == "Please clarify the outcome date."

        edited = await client.put(
            f"/api/v1/testimonials/me/{created['id']}/draft", json=_draft_payload()
        )
        assert edited.status_code == 200
        assert edited.json()["status"] == "draft"

        resubmitted = await _submit(client, created["id"])
        assert resubmitted.status_code == 200
        assert resubmitted.json()["status"] == "submitted"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_internal_notes_are_staff_only_and_never_public(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="story-notes")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await _create_draft(client)
        await _submit(client, created["id"])

    overrides(session, "moderator", uid="mod-notes")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        updated = await client.put(
            f"/api/v1/admin/testimonials/{created['id']}/notes",
            json={"notes": "Award letter looks legitimate, cross-checked with provider site."},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["internal_notes"] == (
            "Award letter looks legitimate, cross-checked with provider site."
        )
        approve = await client.post(
            f"/api/v1/admin/testimonials/{created['id']}/approve",
            json={"reason": "Looks good."},
        )
        assert approve.status_code == 200

    overrides(session, "applicant", uid="story-notes")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        own_view = await client.get(f"/api/v1/testimonials/me/{created['id']}")
        assert "internal_notes" not in own_view.json()

    overrides(session, "applicant", uid="browsing-user-notes")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            public_view = await client.get(
                f"/api/v1/success-stories/{created['slug']}"
            )
            assert "internal_notes" not in public_view.json()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_only_approved_stories_can_be_featured(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="story-h")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await _create_draft(client)
        await _submit(client, created["id"])

    overrides(session, "moderator", uid="mod-2")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            feature = await client.post(f"/api/v1/admin/testimonials/{created['id']}/feature")
            assert feature.status_code == 409
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stats_hide_zero_counts_and_reflect_real_data(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="stats-user")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            empty_stats = await client.get("/api/v1/success-stories/stats")
            assert empty_stats.status_code == 200
            body = empty_stats.json()
            assert body["total_stories"] is None
            assert body["verified_stories"] is None
    finally:
        app.dependency_overrides.clear()

    overrides(session, "applicant", uid="stats-user-2")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await _create_draft(client)
        await _submit(client, created["id"])

    overrides(session, "moderator", uid="admin-2")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            f"/api/v1/admin/testimonials/{created['id']}/approve", json={"reason": "Looks good."}
        )

    overrides(session, "applicant", uid="stats-user-3")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            stats = await client.get("/api/v1/success-stories/stats")
            assert stats.status_code == 200
            body = stats.json()
            assert body["total_stories"] == 1
            assert body["verified_stories"] is None
            assert body["countries_represented"] == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_privacy_toggles_hide_fields_from_public_view(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="story-i")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await _create_draft(
            client,
            privacy={
                "display_mode": "anonymous",
                "show_university": False,
                "show_country": False,
                "show_program": False,
                "show_photo": False,
            },
        )
        await _submit(client, created["id"])

    overrides(session, "moderator", uid="admin-3")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            f"/api/v1/admin/testimonials/{created['id']}/approve", json={"reason": "ok"}
        )

    overrides(session, "applicant", uid="browsing-user-4")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            detail = await client.get(f"/api/v1/success-stories/{created['slug']}")
            body = detail.json()
            assert body["display_name"] == "Anonymous Applicant"
            assert body["university"] is None
            assert body["country"] is None
            assert body["program"] is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_evidence_url_rejects_paths_not_belonging_to_the_testimonial(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="story-j")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await _create_draft(
                client, evidence_storage_paths=["testimonial-evidence/story-j/award.pdf"]
            )
            wrong_path = await client.get(
                f"/api/v1/testimonials/me/{created['id']}/evidence-url",
                params={"path": "testimonial-evidence/someone-else/award.pdf"},
            )
            assert wrong_path.status_code == 404
    finally:
        app.dependency_overrides.clear()
