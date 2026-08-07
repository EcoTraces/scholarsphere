import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from app.core import http_client
from app.core.http_client import ExternalAPIError
from app.services import simpler_grants
from app.services.simpler_grants import SimplerGrantsSource

URL = "https://api.simpler.grants.gov/v1/opportunities/search"


def source_settings(*, api_key: str = "test-api-key") -> SimpleNamespace:
    return SimpleNamespace(
        simpler_grants_api_key=api_key,
        simpler_grants_base_url="https://api.simpler.grants.gov",
    )


def http_settings(*, retries: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        http_timeout_seconds=1,
        http_max_retries=retries,
        http_max_response_bytes=4096,
    )


def opportunity(**updates: object) -> dict[str, object]:
    record: dict[str, object] = {
        "opportunity_id": "abc-123",
        "opportunity_number": "ED-2026-01",
        "opportunity_title": "Education Grant",
        "agency_name": "Department of Education",
        "agency_code": "ED",
        "summary_description": "<p>Support for schools</p>",
        "post_date": "2026-07-01",
        "close_date": "2026-09-30",
        "opportunity_status": "posted",
        "award_floor": "1,000",
        "award_ceiling": "$50,000",
    }
    record.update(updates)
    return record


@pytest.mark.asyncio
async def test_authenticated_request_filters_pagination_sorting_and_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(simpler_grants, "get_settings", source_settings)
    request = AsyncMock(
        return_value={"data": {"opportunities": [opportunity()]}}
    )
    monkeypatch.setattr(simpler_grants, "post_json", request)

    result = await SimplerGrantsSource().collect(
        keyword="education",
        page=3,
        page_size=20,
        statuses=["posted"],
        sort_field="close_date",
        sort_direction="ascending",
    )

    request.assert_awaited_once_with(
        URL,
        json={
            "query": "education",
            "filters": {"opportunity_status": {"one_of": ["posted"]}},
            "pagination": {
                "page_offset": 3,
                "page_size": 20,
                "sort_order": [
                    {
                        "order_by": "close_date",
                        "sort_direction": "ascending",
                    }
                ],
            },
        },
        headers={
            "X-API-Key": "test-api-key",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    assert len(result) == 1
    normalized = result[0]
    assert normalized.source_code == "simpler_grants"
    assert normalized.external_id == "abc-123"
    assert normalized.external_reference == "ED-2026-01"
    assert normalized.title == "Education Grant"
    assert normalized.provider_name == "Department of Education"
    assert normalized.provider_code == "ED"
    assert normalized.opportunity_type == "grant"
    assert normalized.country == "United States"
    assert normalized.currency == "USD"
    assert normalized.award_floor == 1000
    assert normalized.award_ceiling == 50000
    assert str(normalized.official_source_url) == (
        "https://simpler.grants.gov/opportunity/abc-123"
    )


@pytest.mark.asyncio
async def test_default_filters_and_sorting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(simpler_grants, "get_settings", source_settings)
    request = AsyncMock(return_value={"data": []})
    monkeypatch.setattr(simpler_grants, "post_json", request)

    await SimplerGrantsSource().collect()

    payload = request.await_args.kwargs["json"]
    assert payload["filters"] == {
        "opportunity_status": {"one_of": ["posted", "forecasted"]}
    }
    assert payload["pagination"] == {
        "page_offset": 1,
        "page_size": 25,
        "sort_order": [
            {"order_by": "post_date", "sort_direction": "descending"}
        ],
    }


@pytest.mark.asyncio
async def test_missing_api_key_is_a_safe_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        simpler_grants,
        "get_settings",
        lambda: source_settings(api_key=""),
    )
    with pytest.raises(ExternalAPIError, match="not configured"):
        await SimplerGrantsSource().collect()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{}, {"data": None}, {"data": []}])
async def test_empty_data_is_safe(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
) -> None:
    monkeypatch.setattr(simpler_grants, "get_settings", source_settings)
    monkeypatch.setattr(
        simpler_grants, "post_json", AsyncMock(return_value=payload)
    )
    assert await SimplerGrantsSource().collect() == []


@pytest.mark.asyncio
async def test_invalid_dates_and_awards_are_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(simpler_grants, "get_settings", source_settings)
    monkeypatch.setattr(
        simpler_grants,
        "post_json",
        AsyncMock(
            return_value={
                "data": {
                    "opportunities": [
                        opportunity(
                            post_date="not-a-date",
                            close_date={"bad": "value"},
                            award_floor="not-money",
                            award_ceiling=[],
                        )
                    ]
                }
            }
        ),
    )
    normalized = (await SimplerGrantsSource().collect())[0]
    assert normalized.opening_date is None
    assert normalized.deadline is None
    assert normalized.award_floor is None
    assert normalized.award_ceiling is None


@pytest.mark.asyncio
@pytest.mark.parametrize("page,page_size", [(0, 25), (1, 0), (1, 101)])
async def test_invalid_pagination_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    page: int,
    page_size: int,
) -> None:
    monkeypatch.setattr(simpler_grants, "get_settings", source_settings)
    request = AsyncMock()
    monkeypatch.setattr(simpler_grants, "post_json", request)
    with pytest.raises(ValueError):
        await SimplerGrantsSource().collect(page=page, page_size=page_size)
    request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sort_field,sort_direction",
    [("title", "ascending"), ("post_date", "sideways")],
)
async def test_invalid_sorting_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    sort_field: str,
    sort_direction: str,
) -> None:
    monkeypatch.setattr(simpler_grants, "get_settings", source_settings)
    request = AsyncMock()
    monkeypatch.setattr(simpler_grants, "post_json", request)
    with pytest.raises(ValueError):
        await SimplerGrantsSource().collect(
            sort_field=sort_field, sort_direction=sort_direction
        )
    request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        httpx.ReadTimeout("private timeout details"),
        httpx.Response(429),
        httpx.Response(500),
    ],
)
@respx.mock
async def test_transport_failures_are_safe_and_api_key_is_not_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    failure: Exception | httpx.Response,
) -> None:
    monkeypatch.setattr(simpler_grants, "get_settings", source_settings)
    monkeypatch.setattr(http_client, "get_settings", http_settings)
    respx.post(URL).mock(side_effect=failure)

    with caplog.at_level(logging.WARNING), pytest.raises(ExternalAPIError):
        await SimplerGrantsSource().collect()

    assert "test-api-key" not in caplog.text


@pytest.mark.asyncio
@respx.mock
async def test_invalid_json_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(simpler_grants, "get_settings", source_settings)
    monkeypatch.setattr(http_client, "get_settings", http_settings)
    respx.post(URL).mock(return_value=httpx.Response(200, text="not-json"))
    with pytest.raises(ExternalAPIError, match="invalid JSON"):
        await SimplerGrantsSource().collect()
