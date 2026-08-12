from unittest.mock import AsyncMock

import pytest

from app.core.http_client import ExternalAPIError
from app.services import usajobs
from app.services.usajobs import UsaJobsSource


def search_item(**descriptor_overrides: object) -> dict[str, object]:
    descriptor = {
        "PositionID": "ED-2026-0001",
        "PositionTitle": "Student Data Analyst Intern",
        "PositionURI": "https://www.usajobs.gov/job/000000100",
        "ApplyURI": ["https://apply.usajobs.gov/000000100"],
        "OrganizationName": "Department of Education",
        "DepartmentName": "Department of Education",
        "PositionStartDate": "2026-08-01",
        "ApplicationCloseDate": "2026-09-15",
        "UserArea": {
            "Details": {
                "JobSummary": "Support data analysis for federal education programs.",
                "HiringPath": ["Students"],
            }
        },
    }
    descriptor.update(descriptor_overrides)
    return {"MatchedObjectId": "000000100", "MatchedObjectDescriptor": descriptor}


def _source() -> UsaJobsSource:
    source = UsaJobsSource()
    source.api_key = "test-key"
    source.user_agent = "integration-tests@example.test"
    return source


@pytest.mark.asyncio
async def test_search_normalizes_response_and_detects_student_hiring_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = AsyncMock(
        return_value={"SearchResult": {"SearchResultItems": [search_item()]}}
    )
    monkeypatch.setattr(usajobs, "get_json", request)
    source = _source()

    result = await source.collect(keyword="data analyst", page=1, page_size=25)

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "000000100"
    assert opportunity.title == "Student Data Analyst Intern"
    assert opportunity.provider_name == "Department of Education"
    assert opportunity.country == "United States"
    assert opportunity.opportunity_type == "internship"
    assert str(opportunity.deadline) == "2026-09-15"
    assert str(opportunity.opening_date) == "2026-08-01"
    assert str(opportunity.official_application_url).startswith(
        "https://apply.usajobs.gov/"
    )
    assert opportunity.verification_status == "pending"

    call = request.await_args
    assert call.kwargs["headers"]["Authorization-Key"] == "test-key"
    assert call.kwargs["headers"]["Host"] == "data.usajobs.gov"
    assert call.kwargs["headers"]["User-Agent"] == "integration-tests@example.test"
    assert call.kwargs["override_user_agent"] is False
    assert call.kwargs["params"]["Keyword"] == "data analyst"


@pytest.mark.asyncio
async def test_non_student_hiring_path_is_classified_as_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = search_item(**{"UserArea": {"Details": {"HiringPath": ["Public"]}}})
    monkeypatch.setattr(
        usajobs, "get_json", AsyncMock(return_value={"SearchResult": {"SearchResultItems": [item]}})
    )
    opportunity = (await _source().collect())[0]
    assert opportunity.opportunity_type == "job"


@pytest.mark.asyncio
async def test_missing_credentials_raise_before_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = AsyncMock()
    monkeypatch.setattr(usajobs, "get_json", request)
    source = UsaJobsSource()
    source.api_key = ""
    source.user_agent = ""

    with pytest.raises(ExternalAPIError, match="USAJOBS_API_KEY"):
        await source.collect()
    request.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_optional_fields_are_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    item = {
        "MatchedObjectId": "minimal-1",
        "MatchedObjectDescriptor": {"PositionTitle": "Minimal Posting"},
    }
    monkeypatch.setattr(
        usajobs, "get_json", AsyncMock(return_value={"SearchResult": {"SearchResultItems": [item]}})
    )
    opportunity = (await _source().collect())[0]
    assert opportunity.provider_name == "U.S. federal government"
    assert opportunity.deadline is None
    assert opportunity.opening_date is None
    assert opportunity.official_source_url is None
    assert opportunity.opportunity_type == "job"


@pytest.mark.asyncio
async def test_empty_and_malformed_responses_return_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source()
    for payload in [{}, {"SearchResult": {}}, {"SearchResult": {"SearchResultItems": []}}]:
        monkeypatch.setattr(usajobs, "get_json", AsyncMock(return_value=payload))
        assert await source.collect() == []


@pytest.mark.asyncio
async def test_invalid_records_do_not_break_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    malformed = {"MatchedObjectDescriptor": {}}
    monkeypatch.setattr(
        usajobs,
        "get_json",
        AsyncMock(
            return_value={
                "SearchResult": {"SearchResultItems": [malformed, search_item()]}
            }
        ),
    )
    result = await _source().collect()
    assert [item.external_id for item in result] == ["000000100"]


@pytest.mark.asyncio
@pytest.mark.parametrize(("page", "page_size"), [(0, 25), (1, 0), (1, 101)])
async def test_invalid_pagination_is_rejected(
    monkeypatch: pytest.MonkeyPatch, page: int, page_size: int
) -> None:
    request = AsyncMock()
    monkeypatch.setattr(usajobs, "get_json", request)
    with pytest.raises(ValueError):
        await _source().collect(page=page, page_size=page_size)
    request.assert_not_awaited()
