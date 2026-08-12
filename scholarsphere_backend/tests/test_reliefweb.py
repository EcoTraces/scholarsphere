from unittest.mock import AsyncMock

import pytest

from app.core.http_client import ExternalAPIError
from app.services import reliefweb
from app.services.reliefweb import ReliefWebJobsSource, ReliefWebTrainingSource


def job_item(**overrides: object) -> dict[str, object]:
    fields = {
        "title": "Protection Officer",
        "url": "https://reliefweb.int/job/1234567/protection-officer",
        "source": [{"name": "UNHCR", "shortname": "UNHCR"}],
        "country": [{"name": "Chad"}],
        "body": "<p>Support protection monitoring.</p>",
        "date": {"created": "2026-07-01T00:00:00+00:00", "closing": "2026-09-15"},
    }
    fields.update(overrides)
    return {"id": "1234567", "fields": fields}


def training_item(**overrides: object) -> dict[str, object]:
    fields = {
        "title": "Humanitarian Negotiation Workshop",
        "url": "https://reliefweb.int/training/7654321/negotiation-workshop",
        "source": [{"name": "OCHA"}],
        "country": [{"name": "Kenya"}],
        "body": "<p>Three-day workshop on humanitarian negotiation.</p>",
        "date": {
            "created": "2026-07-01T00:00:00+00:00",
            "registration": "2026-08-20",
            "start": "2026-09-01",
            "end": "2026-09-03",
        },
    }
    fields.update(overrides)
    return {"id": "7654321", "fields": fields}


@pytest.mark.asyncio
async def test_jobs_source_normalizes_response(monkeypatch: pytest.MonkeyPatch) -> None:
    request = AsyncMock(return_value={"data": [job_item()]})
    monkeypatch.setattr(reliefweb, "post_json", request)
    source = ReliefWebJobsSource()
    source.appname = "scholarsphere-test"

    result = await source.collect(keyword="protection", page=1, page_size=10)

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "1234567"
    assert opportunity.title == "Protection Officer"
    assert opportunity.provider_name == "UNHCR"
    assert opportunity.country == "Chad"
    assert opportunity.opportunity_type == "internship"
    assert str(opportunity.deadline) == "2026-09-15"
    assert str(opportunity.opening_date) == "2026-07-01"
    assert opportunity.opportunity_status == "posted"
    assert str(opportunity.official_source_url).startswith("https://reliefweb.int/job/")
    assert opportunity.verification_status == "pending"

    call = request.await_args
    assert call.kwargs["params"] == {"appname": "scholarsphere-test"}
    assert call.kwargs["json"]["query"] == {"value": "protection", "operator": "AND"}
    assert call.kwargs["json"]["limit"] == 10
    assert call.kwargs["json"]["offset"] == 0


@pytest.mark.asyncio
async def test_training_source_uses_registration_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = AsyncMock(return_value={"data": [training_item()]})
    monkeypatch.setattr(reliefweb, "post_json", request)
    source = ReliefWebTrainingSource()
    source.appname = "scholarsphere-test"

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.opportunity_type == "training"
    assert str(opportunity.deadline) == "2026-08-20"
    assert opportunity.provider_name == "OCHA"


@pytest.mark.asyncio
async def test_missing_appname_raises_before_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = AsyncMock()
    monkeypatch.setattr(reliefweb, "post_json", request)
    source = ReliefWebJobsSource()
    source.appname = ""

    with pytest.raises(ExternalAPIError, match="RELIEFWEB_APPNAME"):
        await source.collect()
    request.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_optional_fields_are_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    item = {"id": "minimal-1", "fields": {"title": "Minimal Job"}}
    monkeypatch.setattr(reliefweb, "post_json", AsyncMock(return_value={"data": [item]}))
    source = ReliefWebJobsSource()
    source.appname = "scholarsphere-test"

    opportunity = (await source.collect())[0]
    assert opportunity.provider_name == "ReliefWeb partner organization"
    assert opportunity.country is None
    assert opportunity.deadline is None
    assert opportunity.opening_date is None
    assert opportunity.official_source_url is None


@pytest.mark.asyncio
async def test_invalid_records_do_not_break_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reliefweb,
        "post_json",
        AsyncMock(return_value={"data": [{"id": None, "fields": {}}, job_item()]}),
    )
    source = ReliefWebJobsSource()
    source.appname = "scholarsphere-test"

    result = await source.collect()
    assert [item.external_id for item in result] == ["1234567"]


@pytest.mark.asyncio
async def test_empty_and_malformed_responses_return_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ReliefWebJobsSource()
    source.appname = "scholarsphere-test"
    for payload in [{}, {"data": None}, {"data": []}]:
        monkeypatch.setattr(reliefweb, "post_json", AsyncMock(return_value=payload))
        assert await source.collect() == []


@pytest.mark.asyncio
@pytest.mark.parametrize(("page", "page_size"), [(0, 25), (1, 0), (1, 101)])
async def test_invalid_pagination_is_rejected(
    monkeypatch: pytest.MonkeyPatch, page: int, page_size: int
) -> None:
    request = AsyncMock()
    monkeypatch.setattr(reliefweb, "post_json", request)
    source = ReliefWebJobsSource()
    source.appname = "scholarsphere-test"

    with pytest.raises(ValueError):
        await source.collect(page=page, page_size=page_size)
    request.assert_not_awaited()
