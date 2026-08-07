from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.routes import external_opportunities
from app.core.auth import AuthenticatedUser
from app.main import app
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.eu_funding import EUFundingSource
from app.services.grants_gov import GrantsGovSource
from app.services.simpler_grants import SimplerGrantsSource


async def authenticated_officer() -> AuthenticatedUser:
    return AuthenticatedUser(
        uid="verification-user",
        email="officer@example.test",
        email_verified=True,
        role="verificationOfficer",
        permissions=frozenset({"external_sources.preview"}),
    )


def normalized() -> NormalizedExternalOpportunity:
    return NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id="123",
        external_reference="ABC-1",
        title="Education Grant",
        opportunity_type="grant",
        provider_name="Department of Education",
        country="United States",
        opportunity_status="posted",
        raw_payload={"id": "123"},
    )


def test_preview_returns_normalized_records_without_persistence(
    monkeypatch,
) -> None:
    collect = AsyncMock(return_value=[normalized()])
    monkeypatch.setattr(GrantsGovSource, "collect", collect)
    app.dependency_overrides[external_opportunities.preview_access] = (
        authenticated_officer
    )
    try:
        response = TestClient(app).get(
            "/api/v1/external-opportunities/grants-gov/preview",
            params={"keyword": "education", "page": 2, "page_size": 10},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["external_id"] == "123"
    collect.assert_awaited_once_with(
        keyword="education",
        page=2,
        page_size=10,
    )


def test_preview_requires_authentication() -> None:
    response = TestClient(app).get(
        "/api/v1/external-opportunities/grants-gov/preview"
    )
    assert response.status_code == 401


def test_preview_validates_pagination(monkeypatch) -> None:
    collect = AsyncMock()
    monkeypatch.setattr(GrantsGovSource, "collect", collect)
    app.dependency_overrides[external_opportunities.preview_access] = (
        authenticated_officer
    )
    try:
        client = TestClient(app)
        assert (
            client.get(
                "/api/v1/external-opportunities/grants-gov/preview?page=0"
            ).status_code
            == 422
        )
        assert (
            client.get(
                "/api/v1/external-opportunities/grants-gov/preview?page_size=101"
            ).status_code
            == 422
        )
    finally:
        app.dependency_overrides.clear()

    collect.assert_not_awaited()


def test_simpler_preview_passes_approved_filters_without_persistence(
    monkeypatch,
) -> None:
    collect = AsyncMock(return_value=[normalized()])
    monkeypatch.setattr(SimplerGrantsSource, "collect", collect)
    app.dependency_overrides[external_opportunities.preview_access] = (
        authenticated_officer
    )
    try:
        response = TestClient(app).get(
            "/api/v1/external-opportunities/simpler-grants/preview",
            params={
                "keyword": "education",
                "page": 2,
                "page_size": 10,
                "statuses": ["posted"],
                "sort_field": "close_date",
                "sort_direction": "ascending",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    collect.assert_awaited_once_with(
        keyword="education",
        page=2,
        page_size=10,
        statuses=["posted"],
        sort_field="close_date",
        sort_direction="ascending",
    )


def test_eu_preview_passes_approved_filters_without_persistence(
    monkeypatch,
) -> None:
    collect = AsyncMock(return_value=[normalized()])
    monkeypatch.setattr(EUFundingSource, "collect", collect)
    app.dependency_overrides[external_opportunities.preview_access] = (
        authenticated_officer
    )
    try:
        response = TestClient(app).get(
            "/api/v1/external-opportunities/eu-funding/preview",
            params={
                "keyword": "climate",
                "page": 2,
                "page_size": 10,
                "type_codes": ["1", "8"],
                "status_codes": ["31094502"],
                "programme_period": "2021 - 2027",
                "language": "en",
                "sort_field": "deadlineDate",
                "sort_direction": "ASC",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    collect.assert_awaited_once_with(
        keyword="climate",
        page=2,
        page_size=10,
        type_codes=["1", "8"],
        status_codes=["31094502"],
        programme_period="2021 - 2027",
        language="en",
        sort_field="deadlineDate",
        sort_direction="ASC",
    )
