"""Cross-cutting resilience tests for the web-scraper source tier
(app/services/web_scraper_base.py and its subclasses): malformed HTML,
a simulated source layout change, and missing-field fallbacks. Per-source
correctness against real fetched HTML is covered by each source's own
test file (test_cscuk_scholarships.py, test_chevening.py,
test_daad_scholarships.py, test_embassy_announcements.py); these tests
instead probe what happens when a page *doesn't* look like what the
adapter expects, using one representative adapter per scenario rather
than repeating every case five times.
"""

from unittest.mock import AsyncMock

import pytest

from app.services import web_scraper_base
from app.services.cscuk_scholarships import CscukScholarshipsSource
from app.services.embassy_announcements import ChinaEmbassySierraLeoneSource


@pytest.mark.asyncio
async def test_malformed_html_does_not_crash_the_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`html.parser` (the parser this project deliberately uses - see
    web_scraper_base.py, chosen to avoid an extra C-extension dependency)
    is lenient about malformed markup, but the adapter's own logic must
    still not raise on genuinely broken input - it should produce a
    best-effort (possibly empty) result instead of crashing the sync
    task for every other source scheduled alongside it.
    """
    source = CscukScholarshipsSource()
    broken_html = (
        "<html><body><div class='et_pb_text_inner'><h1>Overview"
        "<p>unterminated tags everywhere<div><span>"
        "<a href='/scholarships/commonwealth-broken/'>broken link"
    )

    async def fake_get_html(url: str, **_: object) -> str:
        if url == f"{source.base_url}/scholarships/":
            return broken_html
        return broken_html

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    # Must not raise - a malformed page produces zero or best-effort
    # records, never an unhandled exception.
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_layout_change_with_no_matching_selectors_yields_no_data_not_a_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulates a site redesign that removes every selector this adapter
    depends on (`.et_pb_text_inner`, `h1.entry-title`). The correct
    behavior is a record with a safe fallback title and no fabricated
    section content - never an exception, and never invented data.
    """
    source = CscukScholarshipsSource()
    redesigned_html = (
        "<html><body><main><h2>New Site Design</h2>"
        "<p>Completely different markup structure.</p></main></body></html>"
    )

    async def fake_get_html(url: str, **_: object) -> str:
        return redesigned_html

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    # Discovery will fall back to the seed slug list since no matching
    # programme links are found on the (redesigned) list page.
    result = await source.collect()

    assert len(result) == len(source._SEED_SLUGS)
    for item in result:
        assert item.title == "Untitled Commonwealth Scholarship programme"
        assert item.description is None
        assert item.deadline is None


@pytest.mark.asyncio
async def test_missing_title_falls_back_to_a_safe_default_not_a_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An embassy announcement article with no <title> and no <h1> must
    still produce a valid record with a clearly-labeled placeholder
    title, not raise or silently invent a title."""
    source = ChinaEmbassySierraLeoneSource()
    article_url = f"{source.base_url}/eng/xwdt/202601/no-title-article.htm"

    async def fake_get_html(url: str, **_: object) -> str:
        if url.rstrip("/").endswith("/eng/xwdt"):
            return f'<html><body><a href="{article_url}">Scholarship notice</a></body></html>'
        return "<html><body><div id='article'>No title anywhere on this page.</div></body></html>"

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    assert result[0].title == "Untitled scholarship announcement"


@pytest.mark.asyncio
async def test_discovered_links_to_a_different_host_are_never_followed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Security regression test: a link on an otherwise-trusted,
    vetted page whose own text matches the scholarship-keyword filter but
    whose href points at a third-party host must never be fetched -
    otherwise a compromised/injected link on a trusted domain could make
    this adapter fetch attacker-controlled URLs (see `same_host_https_url`
    in app/services/web_scraper_base.py, and the real, legitimate
    same-host article link that must still work correctly alongside it).
    """
    source = ChinaEmbassySierraLeoneSource()
    legitimate_url = f"{source.base_url}/eng/xwdt/202601/legit-scholarship.htm"
    external_url = "https://attacker.example.test/scholarship-phish"

    async def fake_get_html(url: str, **_: object) -> str:
        if url.rstrip("/").endswith("/eng/xwdt"):
            return (
                f'<a href="{legitimate_url}">Scholarship notice (legitimate)</a>'
                f'<a href="{external_url}">Scholarship notice (external)</a>'
            )
        if url == legitimate_url:
            return (
                "<html><head><title>Legit Scholarship</title></head>"
                "<body><div id='article'>Real content.</div></body></html>"
            )
        raise AssertionError(f"Must never fetch a non-same-host URL: {url}")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    urls_fetched = {str(item.official_source_url) for item in result}
    assert urls_fetched == {legitimate_url}
    assert external_url not in urls_fetched
