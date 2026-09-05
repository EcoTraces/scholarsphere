"""Tests for app/services/erasmus_mundus_source.py, using real fixtures
fetched 2026-08-30 from
https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en
(page 0, page 1, and a genuinely-past-the-last-page response, all saved
unmodified in tests/fixtures/) - proves the pagination_engine.
paginate_by_url integration against a second, independently-verified
real site's own termination behavior, not a synthetic stand-in.
"""

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from app.core.config import get_settings
from app.services import web_scraper_base
from app.services.erasmus_mundus_source import ErasmusMundusJointMastersSource
from app.services.scraper_metrics import get_metrics

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


_PAGE_FIXTURES = {
    "0": _fixture("erasmus_mundus_catalogue_page0.html"),
    "1": _fixture("erasmus_mundus_catalogue_page1.html"),
}
_EMPTY_PAGE = _fixture("erasmus_mundus_catalogue_empty_page.html")


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

    source = ErasmusMundusJointMastersSource()
    results = await source.collect()

    # 20 real cards per real fixture page, but one card on each page
    # (RESCO on page 0, European Forestry on page 1) links to a plain
    # `http://` programme site rather than `https://` - correctly and
    # silently dropped by the shared HTTPS-only enforcement
    # (`absolute_https_url`), never "fixed" by guessing a scheme. So 19
    # (not 20) from each real page, then a genuine zero-card response
    # for page 2 stops the loop.
    assert len(results) == 38
    assert len(calls) == 3
    assert not any("resco" in str(r.official_application_url) for r in results)
    assert not any(
        "europeanforestry" in str(r.official_application_url) for r in results
    )

    first = results[0]
    assert first.title == "Erasmus Mundus Joint Master in Multilingualism and Cultural Diversity"
    assert str(first.official_application_url) == "https://www.multidiverse.eu/"
    assert str(first.official_source_url) == (
        "https://erasmus-plus.ec.europa.eu/projects/search/details/101241136"
    )
    assert first.opportunity_type == "scholarship"
    assert first.opportunity_status == "posted"
    # Genuinely open worldwide, not tied to a single destination country.
    assert first.country is None
    assert first.provider_name == (
        "Erasmus Mundus Joint Masters (European Education and Culture "
        "Executive Agency, European Commission)"
    )
    assert first.description is not None
    assert "MultiDiverse" in first.description
    # No per-programme deadline is stated on this listing page - never
    # guessed from the catalogue's own generic "October and January" text.
    assert first.deadline is None

    second_page_first = results[19]
    assert second_page_first.title == "International Master in Transnational Migrations"


@pytest.mark.asyncio
async def test_collect_deduplicates_by_application_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_html(url: str, **_: object) -> str:
        return _PAGE_FIXTURES["0"]

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)

    source = ErasmusMundusJointMastersSource()
    results = await source.collect()

    # 20 real cards, minus the one non-HTTPS (RESCO) link correctly
    # dropped - see the pagination test above for the full explanation.
    assert len(results) == 19
    external_ids = {r.external_id for r in results}
    assert len(external_ids) == 19


@pytest.mark.asyncio
async def test_collect_returns_empty_list_when_first_page_fetch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.http_client import ExternalAPIError

    async def failing_get_html(url: str, **_: object) -> str:
        raise ExternalAPIError("External page is temporarily unavailable.")

    monkeypatch.setattr(web_scraper_base, "get_html", failing_get_html)

    source = ErasmusMundusJointMastersSource()
    results = await source.collect()

    assert results == []


@pytest.mark.asyncio
async def test_collect_uses_configured_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_urls: list[str] = []

    async def fake_get_html(url: str, **_: object) -> str:
        seen_urls.append(url)
        return _EMPTY_PAGE

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)

    source = ErasmusMundusJointMastersSource()
    await source.collect()

    assert seen_urls[0].startswith(get_settings().erasmus_mundus_base_url)


@pytest.mark.asyncio
async def test_collect_increments_pagination_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    get_metrics().reset()

    async def fake_get_html(url: str, **_: object) -> str:
        return _PAGE_FIXTURES.get(_page_number(url), _EMPTY_PAGE)

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)

    source = ErasmusMundusJointMastersSource()
    await source.collect()

    snapshot = get_metrics().snapshot()
    assert snapshot["pagination_pages"] == 3
