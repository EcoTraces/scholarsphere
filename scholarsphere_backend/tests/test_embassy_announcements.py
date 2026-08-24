from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.core.http_client import ExternalAPIError
from app.services import web_scraper_base
from app.services.embassy_announcements import (
    ChinaEmbassySierraLeoneSource,
    EswatiniSlasSource,
    SierraLeoneMTHESource,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- China Embassy Sierra Leone: real fixtures, fetched 2026-08-22 -------


@pytest.mark.asyncio
async def test_china_embassy_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uses real HTML fetched from sl.china-embassy.gov.cn on 2026-08-22
    (see docs/AUTHORITATIVE_SOURCES.md #11). The live news index carried
    more than one scholarship-titled link at fetch time (the site
    publishes new articles regularly), so this fixture-backed test serves
    the same article content for any matching article URL rather than
    pinning to exactly one, and asserts on the known MOFCOM article by id
    rather than assuming a fixed result count.
    """
    source = ChinaEmbassySierraLeoneSource()
    known_article_url = f"{source.base_url}/eng/xwdt/202604/t20260403_11886183.htm"

    async def fake_get_html(url: str, **_: object) -> str:
        if url.rstrip("/").endswith("/eng/xwdt"):
            return _fixture("china_embassy_news.html")
        if url.startswith(f"{source.base_url}/eng/xwdt/"):
            return _fixture("china_article.html")
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) >= 1
    by_url = {str(item.official_source_url): item for item in result}
    assert known_article_url in by_url
    opportunity = by_url[known_article_url]
    assert "Scholarship" in opportunity.title
    assert opportunity.opportunity_type == "scholarship"
    assert opportunity.country == "China"
    assert "Embassy" in opportunity.provider_name
    assert "China" in opportunity.provider_name
    assert opportunity.official_application_url is None
    assert opportunity.verification_status == "pending"
    assert opportunity.publication_status == "unpublished"
    # This article states a real deadline ("By May 12, 2026 - Email
    # materials...") but in a table/bullet style ("By <date>") that this
    # adapter's deliberately conservative keyword-anchored extractor
    # (see _DEADLINE_KEYWORDS) does not recognize - so it is correctly
    # left None rather than guessed. See the regression test below for
    # why the extractor stays conservative rather than adding a generic
    # "by" keyword to catch this: that keyword is too common in ordinary
    # prose ("supported by...", "administered by...") and would
    # reintroduce the false-positive risk this fix closed. A human
    # officer confirming the deadline against the real article (already
    # required for every record from this adapter) covers this gap.
    assert opportunity.deadline is None


@pytest.mark.asyncio
async def test_china_embassy_unrelated_date_is_not_mistaken_for_a_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression test for a real bug caught by a live smoke test
    (2026-08-22): a "farewell ceremony" article's opening sentence ("On
    August 21, 2026, the Chinese Embassy...") was an event date, not a
    deadline, but the earlier "first date anywhere in the body" extraction
    logic picked it up anyway. Fixed by anchoring on a nearby
    deadline-indicating keyword (see `_DEADLINE_KEYWORDS` in
    app/services/embassy_announcements.py) - this fixture (real HTML,
    fetched live 2026-08-22) has no such keyword anywhere near a date, so
    the correct behavior is `deadline is None`.
    """
    source = ChinaEmbassySierraLeoneSource()
    article_url = f"{source.base_url}/eng/xwdt/202608/t20260822_12008498.htm"

    async def fake_get_html(url: str, **_: object) -> str:
        if url.rstrip("/").endswith("/eng/xwdt"):
            return (
                f'<html><body><a href="{article_url}">2026 Farewell Ceremony '
                "Chinese Government Scholarship Program</a></body></html>"
            )
        if url == article_url:
            return _fixture("china_article_farewell.html")
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    assert result[0].deadline is None


@pytest.mark.asyncio
async def test_china_embassy_non_scholarship_links_are_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real fixture page has many navigation/other-news links; only
    the ones whose own link text mentions a scholarship keyword should be
    treated as candidate articles."""
    source = ChinaEmbassySierraLeoneSource()
    list_url = f"{source.base_url}/eng/xwdt/"
    monkeypatch.setattr(
        web_scraper_base, "get_html", AsyncMock(return_value=_fixture("china_embassy_news.html"))
    )
    soup = await source.fetch_soup(list_url)
    total_links = len(soup.find_all("a", href=True))

    urls = source._matching_article_urls(soup, list_url)

    assert any(url.endswith("t20260403_11886183.htm") for url in urls)
    assert 0 < len(urls) < total_links


@pytest.mark.asyncio
async def test_china_embassy_list_fetch_failure_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ChinaEmbassySierraLeoneSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(side_effect=ExternalAPIError("temporarily unavailable")),
    )

    assert await source.collect() == []


# --- Sierra Leone MTHE: synthetic fixture -------------------------------
#
# LIVE SOURCE TEST: NOT PERFORMED. mthe.gov.sl refused every connection
# attempted from this development environment (see the class docstring in
# app/services/embassy_announcements.py) - this fixture is a realistic
# synthetic approximation of a government ministry news page (same shape
# as the confirmed-real China Embassy fixture above: a list page of
# titled article links, an article page with a body container), not
# captured from the live site. Smoke-test this adapter against the real
# site before trusting it in production - see Task.md.

_SYNTHETIC_MTHE_LIST = """
<html><body>
<div class="news-list">
  <a href="/news/2026-russia-scholarship.html">Government Announces Russian Scholarships for 2026/2027 Academic Year</a>
  <a href="/news/2026-budget.html">Ministry Announces 2026 Budget Priorities</a>
</div>
</body></html>
"""

_SYNTHETIC_MTHE_ARTICLE = """
<html><head><title>Government Announces Russian Scholarships for 2026/2027 Academic Year</title></head>
<body>
<article>
<p>The Ministry of Technical and Higher Education announces scholarship
opportunities for Sierra Leonean students offered by the Government of
the Russian Federation for the 2026/2027 academic year.</p>
<p>The submission deadline is 26 November 2026. Interested applicants
should apply through the Ministry's official application portal.</p>
</article>
</body></html>
"""


@pytest.mark.asyncio
async def test_mthe_collect_normalizes_synthetic_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SierraLeoneMTHESource()
    article_url = f"{source.base_url}/news/2026-russia-scholarship.html"

    async def fake_get_html(url: str, **_: object) -> str:
        if url.rstrip("/") == source.base_url:
            return _SYNTHETIC_MTHE_LIST
        if url == article_url:
            return _SYNTHETIC_MTHE_ARTICLE
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert "Russian Scholarships" in opportunity.title
    assert opportunity.country == "Sierra Leone"
    assert "Ministry of Technical and Higher Education" in opportunity.provider_name
    assert opportunity.deadline is not None
    assert str(opportunity.deadline) == "2026-11-26"
    assert opportunity.verification_status == "pending"


@pytest.mark.asyncio
async def test_mthe_unreachable_site_fails_safe_to_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirrors the real behavior observed against the live site
    (connection refused) - the sync must fail safely (empty batch,
    logged) rather than crash the whole sync task."""
    source = SierraLeoneMTHESource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(side_effect=ExternalAPIError("connection refused")),
    )

    assert await source.collect() == []


# --- Eswatini SLAS: synthetic fixture -------------------------------------
#
# LIVE SOURCE TEST: NOT PERFORMED. slas.gov.sz timed out on every
# connection attempted from this development environment (see the class
# docstring in app/services/embassy_announcements.py) - this fixture is a
# realistic synthetic approximation, not captured from the live site.


_SYNTHETIC_SLAS_LIST = """
<html><body>
<div class="news-list">
  <a href="/news/sadc-scholarship-2027.html">Government of Eswatini Local and SADC Scholarship (PTET Loan) Now Open</a>
  <a href="/news/office-hours.html">Ministry Holiday Office Hours</a>
</div>
</body></html>
"""

_SYNTHETIC_SLAS_ARTICLE = """
<html><head><title>Government of Eswatini Local and SADC Scholarship (PTET Loan) Now Open</title></head>
<body>
<article>
<p>The Ministry of Labour and Social Security announces that applications
for the Local and SADC Scholarship (PTET Loan) for the 2027 academic year
are now open for students wishing to study in Eswatini or in selected
SADC countries.</p>
<p>The application deadline is 15 October 2026. Apply online at
www.slas.gov.sz.</p>
</article>
</body></html>
"""


@pytest.mark.asyncio
async def test_eswatini_slas_collect_normalizes_synthetic_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = EswatiniSlasSource()
    article_url = f"{source.base_url}/news/sadc-scholarship-2027.html"

    async def fake_get_html(url: str, **_: object) -> str:
        if url.rstrip("/") == source.base_url:
            return _SYNTHETIC_SLAS_LIST
        if url == article_url:
            return _SYNTHETIC_SLAS_ARTICLE
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert "SADC Scholarship" in opportunity.title
    assert opportunity.country == "Eswatini"
    assert "Eswatini" in opportunity.provider_name
    assert opportunity.deadline is not None
    assert str(opportunity.deadline) == "2026-10-15"


@pytest.mark.asyncio
async def test_eswatini_slas_unreachable_site_fails_safe_to_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirrors the real behavior observed against the live site (every
    connection attempt timed out) - the sync must fail safely rather
    than crash the whole sync task."""
    source = EswatiniSlasSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(side_effect=ExternalAPIError("connection timed out")),
    )

    assert await source.collect() == []
