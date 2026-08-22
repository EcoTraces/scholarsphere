from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.core.http_client import ExternalAPIError
from app.services import web_scraper_base
from app.services.cscuk_scholarships import CscukScholarshipsSource

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_collect_discovers_and_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uses real HTML fetched from cscuk.fcdo.gov.uk on 2026-08-22 (see
    docs/AUTHORITATIVE_SOURCES.md #8) - not synthetic markup - so this
    test breaks loudly if the site's real structure changes. Every
    discovered detail-page URL is served the same real fixture (a real
    Master's Scholarships page); the assertions below target that one
    programme specifically by its external_id, since discovery order
    off the real list page is not something this test should pin down.
    """
    source = CscukScholarshipsSource()
    list_url = f"{source.base_url}/scholarships/"
    detail_url = f"{source.base_url}/scholarships/commonwealth-masters-scholarships/"

    async def fake_get_html(url: str, **_: object) -> str:
        if url == list_url:
            return _fixture("cscuk_list.html")
        if url.startswith(f"{source.base_url}/scholarships/commonwealth-"):
            return _fixture("cscuk_detail.html")
        raise AssertionError(f"Unexpected URL fetched: {url}")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) >= 1
    by_id = {item.external_id: item for item in result}
    assert "commonwealth-masters-scholarships" in by_id
    opportunity = by_id["commonwealth-masters-scholarships"]
    assert opportunity.title == "Commonwealth Master’s Scholarships"
    assert opportunity.opportunity_type == "scholarship"
    assert opportunity.provider_name == "Commonwealth Scholarship Commission in the UK"
    assert opportunity.country == "United Kingdom"
    assert opportunity.description is not None
    assert "Commonwealth" in opportunity.description
    assert opportunity.verification_status == "pending"
    assert opportunity.publication_status == "unpublished"
    assert str(opportunity.official_source_url) == detail_url


@pytest.mark.asyncio
async def test_falls_back_to_seed_slugs_if_list_page_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = CscukScholarshipsSource()

    async def fake_get_html(url: str, **_: object) -> str:
        if url.rstrip("/").endswith("/scholarships"):
            raise ExternalAPIError("temporarily unavailable")
        return _fixture("cscuk_detail.html")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect(page_size=len(source._SEED_SLUGS))

    assert len(result) == len(source._SEED_SLUGS)
    assert {item.external_id for item in result} == set(source._SEED_SLUGS)


@pytest.mark.asyncio
async def test_missing_deadline_prose_is_left_null_not_guessed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real fixture's 'How to apply' section states the closing date
    without an adjacent year in the same sentence ("...20 October" with
    the academic year mentioned only in an earlier sentence) - this must
    not be guessed at, per the "never invent data" rule.
    """
    source = CscukScholarshipsSource()
    list_url = f"{source.base_url}/scholarships/"

    async def fake_get_html(url: str, **_: object) -> str:
        if url == list_url:
            return _fixture("cscuk_list.html")
        return _fixture("cscuk_detail.html")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    by_id = {item.external_id: item for item in result}
    assert by_id["commonwealth-masters-scholarships"].deadline is None


@pytest.mark.asyncio
async def test_detail_fetch_failure_is_skipped_not_fatal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = CscukScholarshipsSource()

    async def fake_get_html(url: str, **_: object) -> str:
        if url.rstrip("/").endswith("/scholarships"):
            return _fixture("cscuk_list.html")
        raise ExternalAPIError("boom")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert result == []


@pytest.mark.asyncio
async def test_min_request_interval_enforces_a_pause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from time import monotonic

    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(web_scraper_base.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(
        web_scraper_base,
        "_last_request_at",
        {"cscuk.fcdo.gov.uk": monotonic() - 0.5},
    )
    monkeypatch.setattr(
        web_scraper_base, "get_html", AsyncMock(return_value=_fixture("cscuk_detail.html"))
    )

    source = CscukScholarshipsSource()
    await source._fetch_html(f"{source.base_url}/scholarships/x/")

    assert sleeps, "expected a rate-limit sleep before the second-ever request to this host"
