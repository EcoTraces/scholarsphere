"""Tests for app/services/scraper_adapters.py - declarative
selector-driven extraction, mocked at the HTTP layer like every other
`WebScraperSource` wiring test in this suite (see
tests/test_browser_rendering.py's mocked section).
"""

import pytest

from app.services import web_scraper_base
from app.services.scraper_adapters import (
    AdapterSelectors,
    GenericHTMLAdapter,
    GenericJSAdapter,
    GovernmentPortalAdapter,
    SPAAdapter,
    UniversityPortalAdapter,
)

_LISTING_HTML = """
<html><body>
<div class="card">
  <h2 class="title">Fully Funded Master's Scholarship</h2>
  <span class="provider">Ministry of Education</span>
  <p class="description">Covers tuition and a monthly stipend.</p>
  <span class="deadline">2027-01-01</span>
  <a class="apply" href="/apply/1">Apply</a>
</div>
<div class="card">
  <h2 class="title">PhD Fellowship</h2>
  <span class="provider">National Research Council</span>
  <p class="description">Full funding for doctoral candidates.</p>
  <a class="apply" href="https://external.test/apply/2">Apply</a>
</div>
</body></html>
"""


class _FixtureGovernmentSource(GovernmentPortalAdapter):
    source_code = "fixture_government_source"
    list_url = "https://gov.example.test/scholarships"
    provider_name_default = "Default Ministry"
    selectors = AdapterSelectors(
        listing_selector="div.card",
        title_selector="h2.title",
        provider_selector="span.provider",
        description_selector="p.description",
        deadline_selector="span.deadline",
        application_selector="a.apply",
    )


@pytest.mark.asyncio
async def test_generic_html_adapter_extracts_cards_via_declared_selectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_html(url: str, **_: object) -> str:
        return _LISTING_HTML

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)

    results = await _FixtureGovernmentSource().collect()

    assert len(results) == 2
    first, second = results
    assert first["title"] == "Fully Funded Master's Scholarship"
    assert first["provider_name"] == "Ministry of Education"
    assert first["description"] == "Covers tuition and a monthly stipend."
    assert first["deadline_text"] == "2027-01-01"
    assert first["official_application_url"] == "https://gov.example.test/apply/1"

    assert second["title"] == "PhD Fellowship"
    assert second["official_application_url"] == "https://external.test/apply/2"


@pytest.mark.asyncio
async def test_generic_html_adapter_falls_back_to_provider_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Source(UniversityPortalAdapter):
        source_code = "fixture_university_source"
        list_url = "https://uni.example.test/scholarships"
        provider_name_default = "Example University"
        selectors = AdapterSelectors(listing_selector="div.card", title_selector="h2.title")

    async def fake_get_html(url: str, **_: object) -> str:
        return _LISTING_HTML

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)

    results = await _Source().collect()

    assert results[0]["provider_name"] == "Example University"
    # No application_selector configured -> never guessed, stays None.
    assert results[0]["official_application_url"] is None


def test_generic_js_adapter_opts_into_browser_rendering() -> None:
    assert GenericJSAdapter.allow_browser_rendering is True
    assert GenericHTMLAdapter.allow_browser_rendering is False


def test_spa_adapter_opts_into_browser_rendering_by_default() -> None:
    assert SPAAdapter.allow_browser_rendering is True
