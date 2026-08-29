"""Tests for app/services/educationusa_source.py, using real fixtures
fetched 2026-08-29 from https://educationusa.state.gov/find-financial-aid
(page 0, page 1, and a genuinely-past-the-last-page response with zero
results, all saved unmodified in tests/fixtures/) - this proves the real
pagination_engine.paginate_by_url integration terminates correctly
against the site's own actual "no more results" response, not a
synthetic stand-in.
"""

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from app.core.config import get_settings
from app.services import web_scraper_base
from app.services.educationusa_source import EducationUsaFinancialAidSource
from app.services.scraper_metrics import get_metrics

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


_PAGE_FIXTURES = {
    "0": _fixture("educationusa_find_financial_aid_page0.html"),
    "1": _fixture("educationusa_find_financial_aid_page1.html"),
}
_EMPTY_PAGE = _fixture("educationusa_find_financial_aid_empty_page.html")


def _page_number(url: str) -> str:
    query = parse_qs(urlsplit(url).query)
    return query.get("page", ["0"])[0]


@pytest.mark.asyncio
async def test_collect_paginates_through_real_fixtures_and_stops_on_empty_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def fake_get_html(url: str, **_: object) -> str:
        calls.append(url)
        return _PAGE_FIXTURES.get(_page_number(url), _EMPTY_PAGE)

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)

    source = EducationUsaFinancialAidSource()
    results = await source.collect()

    # 10 real rows per real fixture page (0 and 1), then a genuine
    # zero-row response for page 2 stops the loop - never an unbounded
    # crawl through educationusa.state.gov's full ~28-page database.
    assert len(results) == 20
    assert len(calls) == 3

    first = results[0]
    assert first.title == "Nonresident Tuition Waiver (NTW) Scholarships"
    assert first.provider_name == "University of Wisconsin-Superior"
    assert first.country == "United States"
    assert first.opportunity_type == "scholarship"
    assert first.opportunity_status == "posted"
    assert (
        str(first.official_source_url)
        == "https://educationusa.state.gov/scholarships/nonresident-tuition-waiver-ntw-scholarships"
    )
    assert str(first.official_application_url) == str(first.official_source_url)
    assert first.description == "Apply by: Fall semester: July 1st; Spring semester: November 1st"
    # Never invented - this platform has no per-record award-amount field
    # extracted from this listing page, so it must stay unset, not guessed.
    assert first.award_floor is None

    second_page_first = results[10]
    assert second_page_first.title == "Public Service Fellows Scholarship Program"


@pytest.mark.asyncio
async def test_collect_deduplicates_by_detail_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """A misbehaving/looping server that serves the same page twice must
    not produce duplicate opportunities - paginate_by_url's own
    key-based dedup (keyed on detail_url here) prevents that.
    """

    async def fake_get_html(url: str, **_: object) -> str:
        # Every page returns the same real page-0 content - the second
        # "page" yields zero *new* records, so the loop stops itself.
        return _PAGE_FIXTURES["0"]

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)

    source = EducationUsaFinancialAidSource()
    results = await source.collect()

    assert len(results) == 10
    external_ids = {r.external_id for r in results}
    assert len(external_ids) == 10


@pytest.mark.asyncio
async def test_collect_returns_empty_list_when_first_page_fetch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.http_client import ExternalAPIError

    async def failing_get_html(url: str, **_: object) -> str:
        raise ExternalAPIError("External page is temporarily unavailable.")

    monkeypatch.setattr(web_scraper_base, "get_html", failing_get_html)

    source = EducationUsaFinancialAidSource()
    results = await source.collect()

    assert results == []


@pytest.mark.asyncio
async def test_collect_uses_configured_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_urls: list[str] = []

    async def fake_get_html(url: str, **_: object) -> str:
        seen_urls.append(url)
        return _EMPTY_PAGE

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)

    source = EducationUsaFinancialAidSource()
    await source.collect()

    assert seen_urls[0].startswith(get_settings().educationusa_base_url)


@pytest.mark.asyncio
async def test_collect_increments_pagination_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    get_metrics().reset()

    async def fake_get_html(url: str, **_: object) -> str:
        return _PAGE_FIXTURES.get(_page_number(url), _EMPTY_PAGE)

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)

    source = EducationUsaFinancialAidSource()
    await source.collect()

    snapshot = get_metrics().snapshot()
    assert snapshot["pagination_pages"] == 3
