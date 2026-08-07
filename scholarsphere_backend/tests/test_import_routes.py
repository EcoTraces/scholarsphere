from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.routes import external_opportunities
from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.main import app
from app.schemas.external_opportunity import (
    ImportStatistics,
    NormalizedExternalOpportunity,
)
from app.services.grants_gov import GrantsGovSource


def user(role: str) -> AuthenticatedUser:
    return AuthenticatedUser(
        uid=f"{role}-user",
        email=f"{role}@example.test",
        email_verified=True,
        role=role,
        permissions=frozenset(),
    )


def record() -> NormalizedExternalOpportunity:
    return NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id="route-1",
        title="Route Grant",
        opportunity_type="grant",
        provider_name="Agency",
        opportunity_status="posted",
        raw_payload={"id": "route-1"},
    )


def test_import_requires_authentication() -> None:
    response = TestClient(app).post(
        "/api/v1/external-opportunities/grants-gov/import"
    )
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["applicant", "opportunityProvider", "moderator"])
def test_non_import_roles_are_denied(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: user(role)
    try:
        response = TestClient(app).post(
            "/api/v1/external-opportunities/grants-gov/import"
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.parametrize(
    "role", ["verificationOfficer", "administrator", "superAdministrator"]
)
def test_authorized_roles_can_import(
    role: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collect = AsyncMock(return_value=[record()])
    persist = AsyncMock(return_value=ImportStatistics(records_created=1))
    monkeypatch.setattr(GrantsGovSource, "collect_for_import", collect)
    monkeypatch.setattr(external_opportunities, "import_opportunities", persist)

    async def current_user() -> AuthenticatedUser:
        return user(role)

    async def database():
        yield object()

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database
    try:
        response = TestClient(app).post(
            "/api/v1/external-opportunities/grants-gov/import"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["records_created"] == 1
    assert persist.await_args.kwargs == {
        "source_code": "grants_gov",
        "actor_id": f"{role}-user",
    }


def test_preview_still_does_not_call_import_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collect = AsyncMock(return_value=[record()])
    persist = AsyncMock()
    monkeypatch.setattr(GrantsGovSource, "collect", collect)
    monkeypatch.setattr(external_opportunities, "import_opportunities", persist)
    app.dependency_overrides[external_opportunities.preview_access] = (
        lambda: user("verificationOfficer")
    )
    try:
        response = TestClient(app).get(
            "/api/v1/external-opportunities/grants-gov/preview"
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    persist.assert_not_awaited()
