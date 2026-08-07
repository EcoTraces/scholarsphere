from unittest.mock import AsyncMock

import pytest

from app.core.http_client import ExternalAPIError
from app.services import grants_gov
from app.services.grants_gov import GrantsGovSource


@pytest.mark.asyncio
async def test_successful_response_is_normalized(
    monkeypatch: pytest.MonkeyPatch,
    grants_hit: dict[str, object],
) -> None:
    request = AsyncMock(return_value={"data": {"oppHits": [grants_hit]}})
    monkeypatch.setattr(grants_gov, "post_json", request)

    result = await GrantsGovSource().collect(
        keyword="education",
        page=2,
        page_size=10,
    )

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "123"
    assert opportunity.external_reference == "ABC-2026-001"
    assert opportunity.title == "Education Innovation Grant"
    assert opportunity.provider_code == "ED"
    assert opportunity.provider_name == "Department of Education"
    assert str(opportunity.opening_date) == "2026-07-01"
    assert str(opportunity.deadline) == "2026-08-31"
    assert opportunity.opportunity_status == "posted"
    assert str(opportunity.official_source_url).endswith("/ABC-2026-001")
    assert opportunity.verification_status == "pending"
    assert opportunity.publication_status == "unpublished"
    assert opportunity.raw_payload == grants_hit

    payload = request.await_args.kwargs["json"]
    assert payload == {
        "rows": 10,
        "startRecordNum": 10,
        "keyword": "education",
        "oppNum": "",
        "eligibilities": "",
        "agencies": "",
        "oppStatuses": "posted|forecasted",
        "aln": "",
        "fundingCategories": "",
    }


@pytest.mark.asyncio
async def test_search_request_supports_all_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = AsyncMock(return_value={"data": {"oppHits": []}})
    monkeypatch.setattr(grants_gov, "post_json", request)

    await GrantsGovSource().search_raw(
        page=3,
        page_size=20,
        statuses=["posted"],
        agencies=["ED", "HHS"],
        funding_categories=["ED"],
        eligibility_codes=["00", "01"],
        assistance_listing="84.123",
        opportunity_number="ABC-1",
    )

    assert request.await_args.kwargs["json"] == {
        "rows": 20,
        "startRecordNum": 40,
        "keyword": "",
        "oppNum": "ABC-1",
        "eligibilities": "00|01",
        "agencies": "ED|HHS",
        "oppStatuses": "posted",
        "aln": "84.123",
        "fundingCategories": "ED",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{}, {"data": None}, {"data": {"oppHits": []}}])
async def test_empty_responses_return_empty_list(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
) -> None:
    monkeypatch.setattr(grants_gov, "post_json", AsyncMock(return_value=payload))

    assert await GrantsGovSource().collect() == []


@pytest.mark.asyncio
async def test_missing_optional_fields_and_invalid_dates_are_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hit = {
        "id": "minimal-1",
        "title": "Minimal Grant",
        "openDate": "invalid",
        "closeDate": [],
    }
    monkeypatch.setattr(
        grants_gov,
        "post_json",
        AsyncMock(return_value={"data": {"oppHits": [hit]}}),
    )

    opportunity = (await GrantsGovSource().collect())[0]
    assert opportunity.external_reference is None
    assert opportunity.provider_code is None
    assert opportunity.provider_name == "United States Government"
    assert opportunity.opening_date is None
    assert opportunity.deadline is None
    assert opportunity.official_source_url is None


@pytest.mark.asyncio
async def test_invalid_records_do_not_break_preview(
    monkeypatch: pytest.MonkeyPatch,
    grants_hit: dict[str, object],
) -> None:
    monkeypatch.setattr(
        grants_gov,
        "post_json",
        AsyncMock(
            return_value={
                "data": {
                    "oppHits": [
                        {"title": "Missing identifier"},
                        grants_hit,
                    ]
                }
            }
        ),
    )

    result = await GrantsGovSource().collect()
    assert [item.external_id for item in result] == ["123"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("page", "page_size"),
    [(0, 25), (1, 0), (1, 101)],
)
async def test_invalid_pagination_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    page: int,
    page_size: int,
) -> None:
    request = AsyncMock()
    monkeypatch.setattr(grants_gov, "post_json", request)

    with pytest.raises(ValueError):
        await GrantsGovSource().collect(page=page, page_size=page_size)
    request.assert_not_awaited()


@pytest.mark.asyncio
async def test_external_errors_are_not_exposed_or_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = ExternalAPIError("External API is temporarily unavailable.")
    monkeypatch.setattr(grants_gov, "post_json", AsyncMock(side_effect=failure))

    with pytest.raises(ExternalAPIError) as captured:
        await GrantsGovSource().collect()
    assert captured.value is failure
