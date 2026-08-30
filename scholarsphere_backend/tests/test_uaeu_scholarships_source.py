"""Tests for app/services/uaeu_scholarships_source.py, using a real
fixture fetched 2026-08-30 from
https://www.uaeu.ac.ae/en/cgs/scholarship.shtml, saved unmodified in
tests/fixtures/. This project's first university-typed source, and the
first that deliberately extracts multiple records with mixed nationality
eligibility, verbatim, for human review - never filtered by this
adapter itself (see the module's own docstring for why).
"""

from pathlib import Path

import pytest

from app.core.http_client import ExternalAPIError
from app.services import web_scraper_base
from app.services.uaeu_scholarships_source import UaeuScholarshipsSource

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_collect_extracts_every_accordion_item_from_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_html(url: str, **_: object) -> str:
        return _fixture("uaeu_scholarship.html")

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)

    source = UaeuScholarshipsSource()
    results = await source.collect()

    # 13 real accordion items on the live page at fetch time - every one
    # extracted, never silently dropped or pre-filtered by eligibility.
    assert len(results) == 13
    titles = {r.title for r in results}
    assert "Graduate Research Assistantship (All nationalities)" in titles
    assert "PhD Fellowship (All Nationalities)" in titles
    # A nationality-restricted title is captured verbatim too - this
    # adapter never filters by eligibility, a human reviewer does.
    assert any("UAE nationals" in t for t in titles)

    fellowship = next(
        r for r in results if r.title == "PhD Fellowship (All Nationalities)"
    )
    assert fellowship.country == "United Arab Emirates"
    assert fellowship.provider_name == (
        "United Arab Emirates University (UAEU), College of Graduate Studies"
    )
    assert fellowship.opportunity_type == "scholarship"
    assert fellowship.opportunity_status == "posted"
    assert str(fellowship.official_application_url) == (
        "https://www.uaeu.ac.ae/en/cgs/phd_fellowship_all.shtml"
    )
    assert str(fellowship.official_source_url) == str(
        fellowship.official_application_url
    )

    # A PDF "details" link is stored as-is, never fetched/parsed itself.
    biology = next(
        r
        for r in results
        if r.title == "Ph.D. Studentship at the Department of Biology"
    )
    assert str(biology.official_application_url).endswith(".pdf")

    # A real page artifact (multiple spaces / a non-breaking space in the
    # source HTML) is preserved verbatim by the shared `clean_text`
    # utility - never silently "fixed" beyond what that utility already
    # does for every other source in this project.
    ride_scholarship = next(
        r for r in results if "Ride Scholarship" in r.title
    )
    assert "Full   Ride Scholarship\xa0from Master to PhD" in ride_scholarship.title


@pytest.mark.asyncio
async def test_collect_returns_empty_list_when_fetch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_get_html(url: str, **_: object) -> str:
        raise ExternalAPIError("External page is temporarily unavailable.")

    monkeypatch.setattr(web_scraper_base, "get_html", failing_get_html)

    source = UaeuScholarshipsSource()
    results = await source.collect()

    assert results == []


@pytest.mark.asyncio
async def test_collect_returns_empty_list_when_accordion_container_is_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirrors this project's standard graceful-degradation pattern for a
    site redesign - a missing/renamed container must never crash the
    sync task, just yield nothing to review.
    """

    async def fake_get_html(url: str, **_: object) -> str:
        return "<html><body><p>Redesigned page.</p></body></html>"

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)

    source = UaeuScholarshipsSource()
    results = await source.collect()

    assert results == []
