from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.core.http_client import ExternalAPIError
from app.services import web_scraper_base
from app.services.chevening import CheveningSource

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_collect_normalizes_real_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """Uses real HTML fetched from chevening.org on 2026-08-22 (see
    docs/AUTHORITATIVE_SOURCES.md #9)."""
    source = CheveningSource()

    async def fake_get_html(url: str, **_: object) -> str:
        if url.rstrip("/").endswith("/scholarships"):
            return _fixture("chevening_list.html")
        if url.rstrip("/").endswith("/apply"):
            return _fixture("chevening_apply.html")
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.title == "Chevening Scholarships"
    assert opportunity.external_id == "chevening-scholarship"
    assert opportunity.opportunity_type == "scholarship"
    assert opportunity.provider_name.startswith("Chevening")
    assert opportunity.deadline == date(2026, 10, 6)
    assert opportunity.description is not None
    assert opportunity.verification_status == "pending"
    assert opportunity.publication_status == "unpublished"


@pytest.mark.asyncio
async def test_apply_page_failure_still_returns_opportunity_without_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = CheveningSource()

    async def fake_get_html(url: str, **_: object) -> str:
        if url.rstrip("/").endswith("/scholarships"):
            return _fixture("chevening_list.html")
        raise ExternalAPIError("temporarily unavailable")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    assert result[0].deadline is None


@pytest.mark.asyncio
async def test_overview_page_failure_returns_no_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = CheveningSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(side_effect=ExternalAPIError("temporarily unavailable")),
    )

    assert await source.collect() == []


@pytest.mark.asyncio
async def test_resyncing_produces_the_same_external_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chevening runs one recurring annual programme, not a catalogue - a
    stable external_id means re-syncing updates the same record rather
    than creating a new one every year (see module docstring)."""
    source = CheveningSource()

    async def fake_get_html(url: str, **_: object) -> str:
        if url.rstrip("/").endswith("/scholarships"):
            return _fixture("chevening_list.html")
        return _fixture("chevening_apply.html")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    first = await source.collect()
    second = await source.collect()

    assert first[0].external_id == second[0].external_id
