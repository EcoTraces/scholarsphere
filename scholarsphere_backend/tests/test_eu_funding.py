import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from app.core import http_client
from app.core.http_client import ExternalAPIError
from app.services import eu_funding
from app.services.eu_funding import EUFundingSource

URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"


def source_settings() -> SimpleNamespace:
    return SimpleNamespace(
        eu_funding_api_url=URL,
        eu_funding_api_key="SEDIA",
        eu_funding_type_codes=["1", "2", "8"],
        eu_funding_status_codes=["31094501", "31094502"],
        eu_funding_type_mappings={
            "1": "grant",
            "2": "grant",
            "8": "cascade_funding",
        },
        eu_funding_status_mappings={
            "31094501": "forthcoming",
            "31094502": "open",
            "31094503": "closed",
        },
        eu_funding_programme_period="2021 - 2027",
        eu_funding_language="en",
        eu_funding_display_fields=[
            "type",
            "identifier",
            "reference",
            "callccm2Id",
            "title",
            "status",
            "caName",
            "projectAcronym",
            "startDate",
            "description",
            "deadlineDate",
            "deadlineModel",
            "frameworkProgramme",
            "programmePeriod",
            "typesOfAction",
            "budgetOverview",
            "keywords",
        ],
    )


def http_settings(*, retries: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        http_timeout_seconds=1,
        http_max_retries=retries,
        http_max_response_bytes=8192,
    )


def record(metadata: object = None, **updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "metadata": metadata,
        "id": "fallback-id",
    }
    value.update(updates)
    return value


@pytest.mark.asyncio
async def test_multipart_request_parameters_names_and_json_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(eu_funding, "get_settings", source_settings)
    request = AsyncMock(return_value={"results": []})
    monkeypatch.setattr(eu_funding, "post_json", request)

    await EUFundingSource().collect(
        keyword="climate",
        page=2,
        page_size=50,
        type_codes=["1", "8"],
        status_codes=["31094502"],
        programme_period="2021 - 2027",
        language="en",
        sort_field="deadlineDate",
        sort_direction="ASC",
    )

    kwargs = request.await_args.kwargs
    assert request.await_args.args == (URL,)
    assert kwargs["params"] == {
        "apiKey": "SEDIA",
        "text": "climate",
        "pageSize": 50,
        "pageNumber": 2,
    }
    assert set(kwargs["files"]) == {
        "query",
        "languages",
        "sort",
        "displayFields",
    }
    files = kwargs["files"]
    assert json.loads(files["query"][1]) == {
        "bool": {
            "must": [
                {"terms": {"type": ["1", "8"]}},
                {"terms": {"status": ["31094502"]}},
                {"term": {"programmePeriod": "2021 - 2027"}},
            ]
        }
    }
    assert json.loads(files["languages"][1]) == ["en"]
    assert json.loads(files["sort"][1]) == {
        "field": "deadlineDate",
        "order": "ASC",
    }
    assert json.loads(files["displayFields"][1]) == source_settings().eu_funding_display_fields


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metadata",
    [
        {
            "identifier": "scalar-id",
            "reference": "REF-1",
            "title": "Scalar title",
            "type": "1",
            "status": "31094502",
        },
        {
            "identifier": ["list-id"],
            "reference": ["REF-2"],
            "title": ["List title"],
            "type": ["8"],
            "status": ["31094501"],
        },
        None,
    ],
)
async def test_scalar_list_and_null_metadata_are_safe(
    monkeypatch: pytest.MonkeyPatch,
    metadata: object,
) -> None:
    monkeypatch.setattr(eu_funding, "get_settings", source_settings)
    item = record(metadata)
    if metadata is None:
        item.update(
            identifier="record-id",
            title="Record title",
            type="2",
            status="31094503",
        )
    monkeypatch.setattr(
        eu_funding,
        "post_json",
        AsyncMock(return_value={"results": [item]}),
    )

    normalized = (await EUFundingSource().collect())[0]
    assert normalized.external_id in {"scalar-id", "list-id", "record-id"}
    assert normalized.provider_name == "European Commission"
    assert normalized.country == "European Union"
    assert normalized.currency == "EUR"


@pytest.mark.asyncio
async def test_metadata_list_and_object_values_are_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(eu_funding, "get_settings", source_settings)
    metadata = [
        {"name": "identifier", "value": {"value": "object-id"}},
        {"name": "reference", "values": ["REF-OBJECT"]},
        {"name": "title", "value": {"label": "Object title"}},
        {"name": "type", "value": "1"},
        {"name": "status", "value": "31094502"},
        {"name": "caName", "value": {"name": "Research Agency"}},
    ]
    monkeypatch.setattr(
        eu_funding,
        "post_json",
        AsyncMock(return_value={"results": [record(metadata)]}),
    )
    normalized = (await EUFundingSource().collect())[0]
    assert normalized.external_id == "object-id"
    assert normalized.external_reference == "REF-OBJECT"
    assert normalized.title == "Object title"
    assert normalized.provider_name == "Research Agency"
    assert normalized.opportunity_type == "grant"
    assert normalized.opportunity_status == "open"


@pytest.mark.asyncio
async def test_missing_metadata_and_malformed_optional_fields_do_not_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(eu_funding, "get_settings", source_settings)
    item = {
        "id": "only-id",
        "identifier": "only-id",
        "title": {"unexpected": "shape"},
        "deadlineDate": {"bad": object()},
        "budgetOverview": {"amount": "not-money"},
    }
    monkeypatch.setattr(
        eu_funding,
        "post_json",
        AsyncMock(return_value={"results": [item]}),
    )
    normalized = (await EUFundingSource().collect())[0]
    assert normalized.external_id == "only-id"
    assert normalized.title == "Untitled opportunity"
    assert normalized.deadline is None
    assert normalized.award_floor is None
    assert normalized.award_ceiling is None


@pytest.mark.asyncio
async def test_earliest_valid_deadline_and_budget_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(eu_funding, "get_settings", source_settings)
    metadata = {
        "identifier": "budget-object",
        "title": "Budget object",
        "deadlineDate": ["invalid", "2026-12-01", "2026-09-15"],
        "budgetOverview": {"min": "1,500", "max": "20,000"},
    }
    monkeypatch.setattr(
        eu_funding,
        "post_json",
        AsyncMock(return_value={"results": [record(metadata)]}),
    )
    normalized = (await EUFundingSource().collect())[0]
    assert str(normalized.deadline) == "2026-09-15"
    assert normalized.award_floor == 1500
    assert normalized.award_ceiling == 20000


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "budget,expected",
    [
        ([{"amount": "100"}, {"totalBudget": "900"}], (100, 900)),
        ([], (None, None)),
        (None, (None, None)),
    ],
)
async def test_budget_lists_and_empty_budgets(
    monkeypatch: pytest.MonkeyPatch,
    budget: object,
    expected: tuple[int | None, int | None],
) -> None:
    monkeypatch.setattr(eu_funding, "get_settings", source_settings)
    metadata = {
        "identifier": "budget-list",
        "title": "Budget list",
        "budgetOverview": budget,
    }
    monkeypatch.setattr(
        eu_funding,
        "post_json",
        AsyncMock(return_value={"results": [record(metadata)]}),
    )
    normalized = (await EUFundingSource().collect())[0]
    assert (normalized.award_floor, normalized.award_ceiling) == expected


@pytest.mark.asyncio
async def test_html_decoding_sanitization_and_result_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(eu_funding, "get_settings", source_settings)
    metadata = {
        "identifier": "html-id",
        "title": "Research &amp; Innovation",
        "description": "<p>Safe &amp; sound</p><script>secret()</script>",
    }
    item = record(metadata, resultUrl="https://example.eu/result/html-id")
    monkeypatch.setattr(
        eu_funding,
        "post_json",
        AsyncMock(return_value={"results": [item]}),
    )
    normalized = (await EUFundingSource().collect())[0]
    assert normalized.title == "Research & Innovation"
    assert "Safe &amp; sound" in (normalized.description or "")
    assert "script" not in (normalized.description or "")
    assert "secret" not in (normalized.description or "")
    assert str(normalized.official_source_url) == "https://example.eu/result/html-id"


@pytest.mark.asyncio
async def test_fallback_url_uses_reference_then_identifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(eu_funding, "get_settings", source_settings)
    request = AsyncMock(
        return_value={
            "results": [
                record(
                    {
                        "identifier": "identifier-1",
                        "reference": "HORIZON-REF 1",
                        "title": "With reference",
                    }
                ),
                record(
                    {"identifier": "identifier-2", "title": "Without reference"}
                ),
            ]
        }
    )
    monkeypatch.setattr(eu_funding, "post_json", request)
    first, second = await EUFundingSource().collect()
    assert str(first.official_source_url).endswith("/HORIZON-REF%201")
    assert str(second.official_source_url).endswith("/identifier-2")


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
async def test_transport_failures_are_safe(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception | httpx.Response,
) -> None:
    monkeypatch.setattr(eu_funding, "get_settings", source_settings)
    monkeypatch.setattr(http_client, "get_settings", http_settings)
    respx.post(URL).mock(side_effect=failure)
    with pytest.raises(ExternalAPIError):
        await EUFundingSource().collect()


@pytest.mark.asyncio
@respx.mock
async def test_invalid_json_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(eu_funding, "get_settings", source_settings)
    monkeypatch.setattr(http_client, "get_settings", http_settings)
    respx.post(URL).mock(return_value=httpx.Response(200, text="not-json"))
    with pytest.raises(ExternalAPIError, match="invalid JSON"):
        await EUFundingSource().collect()
