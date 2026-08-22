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
