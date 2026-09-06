from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.core.http_client import ExternalAPIError
from app.services import web_scraper_base
from app.services.daad_scholarships import DaadScholarshipsSource

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_collect_normalizes_real_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """Uses real HTML fetched from www2.daad.de on 2026-08-22 for a
    detail id from the configured seed list (see
    docs/AUTHORITATIVE_SOURCES.md #10)."""
    source = DaadScholarshipsSource()
    source.detail_ids = ["50026200"]
    monkeypatch.setattr(
        web_scraper_base, "get_html", AsyncMock(return_value=_fixture("daad_detail.html"))
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "50026200"
    assert opportunity.opportunity_type == "scholarship"
    assert opportunity.provider_name == "DAAD (German Academic Exchange Service)"
    assert opportunity.country == "Germany"
    assert "DAAD" not in opportunity.title  # title suffix stripped, not the raw <title>
    assert opportunity.title
    assert opportunity.verification_status == "pending"
    assert opportunity.publication_status == "unpublished"
    assert "detail=50026200" in str(opportunity.official_source_url)


@pytest.mark.asyncio
async def test_only_configured_seed_ids_are_fetched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = DaadScholarshipsSource()
    source.detail_ids = ["111", "222"]
    fetch = AsyncMock(return_value=_fixture("daad_detail.html"))
    monkeypatch.setattr(web_scraper_base, "get_html", fetch)

    result = await source.collect()

    assert {item.external_id for item in result} == {"111", "222"}
    assert fetch.await_count == 2


@pytest.mark.asyncio
async def test_one_failed_detail_fetch_does_not_break_the_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = DaadScholarshipsSource()
    source.detail_ids = ["good", "bad"]

    async def fake_get_html(url: str, **_: object) -> str:
        if "detail=bad" in url:
            raise ExternalAPIError("temporarily unavailable")
        return _fixture("daad_detail.html")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert [item.external_id for item in result] == ["good"]


@pytest.mark.asyncio
async def test_no_year_adjacent_deadline_text_is_left_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real fixture's page says deadlines are 'updated annually' with
    no fixed current-cycle date - must not be guessed at."""
    source = DaadScholarshipsSource()
    source.detail_ids = ["50026200"]
    monkeypatch.setattr(
        web_scraper_base, "get_html", AsyncMock(return_value=_fixture("daad_detail.html"))
    )

    result = await source.collect()

    assert result[0].deadline is None


@pytest.mark.asyncio
async def test_kas_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Konrad-Adenauer-Stiftung (KAS): Scholarship Programme for
    International Students (detail id 10000108) - added 2026-09-06 in
    response to a request for another fully funded Master's scholarship
    in Germany. Real HTML fetched from www2.daad.de on 2026-09-06.

    Genuinely fully funded per `_FUNDING_TYPE_OVERRIDES`: a monthly
    grant of EUR 992 (Germany's standard BAfoeG maximum living-cost
    rate) plus health/long-term-care insurance and family allowances,
    and German public universities charge no tuition for a first
    Master's degree in 15 of 16 federal states (Baden-Wuerttemberg's
    narrower non-EU tuition fee is the one documented exception, noted
    in the source rather than hidden).

    The live page's own country-eligibility dropdown lists "Sierra
    Leone" by name (confirmed directly against the live site during
    research) - though that dropdown text falls past the shared
    adapter's 5000-character description truncation for this
    particular (longer than usual) page, so it is not itself asserted
    on the stored `description` here.

    No deadline extracted: the page states "Closing date for
    applications is 15 July (12 o'clock noon) of each year" - a
    real, recurring annual cycle with no year attached, so
    `extract_confident_date_after` correctly resolves to `None` rather
    than guessing a year - the same pattern already covered by
    `test_no_year_adjacent_deadline_text_is_left_null` for a different
    detail id."""
    source = DaadScholarshipsSource()
    source.detail_ids = ["10000108"]
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("daad_detail_kas.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "10000108"
    assert (
        opportunity.title
        == "Konrad-Adenauer-Stiftung (KAS): Scholarship Programme for International Students"
    )
    assert opportunity.country == "Germany"
    assert opportunity.provider_name == "DAAD (German Academic Exchange Service)"
    assert opportunity.description is not None
    assert "992 EUR" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_other_seed_ids_keep_no_funding_type_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The five original seed ids were never individually researched for
    funding completeness - adding the KAS override must not retroactively
    assign them a classification."""
    from app.services.daad_scholarships import _FUNDING_TYPE_OVERRIDES

    for original_id in (
        "50026200",
        "50076777",
        "57742121",
        "57742130",
        "57135739",
        "10000486",
    ):
        assert _FUNDING_TYPE_OVERRIDES.get(original_id) is None
