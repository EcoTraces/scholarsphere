"""Tests for app/services/mastercard_foundation_scholars_source.py, using
a real fixture fetched 2026-09-05 from
https://mastercardfdn.org/assets/json/institution.json, saved unmodified
in tests/fixtures/. This project's first source whose "many opportunities
from one organization" shape comes from a plain static JSON asset rather
than parsed HTML, and the first that must de-duplicate bilingual
(English/French) locale entries mixed into a single flat array.
"""

from pathlib import Path

import pytest

from app.core.http_client import ExternalAPIError
from app.services import mastercard_foundation_scholars_source as source_module
from app.services.mastercard_foundation_scholars_source import (
    MastercardFoundationScholarsSource,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_collect_extracts_every_english_institution_from_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_html(url: str, **_: object) -> str:
        return _fixture("mastercard_foundation_institutions.json")

    monkeypatch.setattr(source_module, "get_html", fake_get_html)

    source = MastercardFoundationScholarsSource()
    results = await source.collect()

    # The real fixture mixes English and French locale duplicates of every
    # institution (59 total entries) - exactly 31 unique English-language
    # institutions at fetch time, never double-counted.
    assert len(results) == 31
    external_ids = {r.external_id for r in results}
    assert len(external_ids) == 31

    ashesi = next(r for r in results if "Ashesi University" in r.title)
    assert ashesi.title == "Ashesi University — Mastercard Foundation Scholars Program"
    assert ashesi.provider_name == "The Mastercard Foundation"
    assert ashesi.opportunity_type == "scholarship"
    assert ashesi.country == "Ghana"
    assert str(ashesi.official_source_url) == (
        "https://mastercardfdn.org/en/what-we-do/our-programs/"
        "mastercard-foundation-scholars-program/where-to-apply/"
        "ashesi-university/"
    )
    assert str(ashesi.official_application_url) == str(ashesi.official_source_url)
    assert "Berekuso" in ashesi.description
    assert "Undergraduate" in ashesi.description

    # A record with no country data in the source at all gets None, never
    # a guessed/invented country - real gap in the fixture (University of
    # British Columbia's `country` list is empty there).
    ubc = next(r for r in results if "University of British Columbia" in r.title)
    assert ubc.country is None


@pytest.mark.asyncio
async def test_collect_reports_application_status_honestly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_html(url: str, **_: object) -> str:
        return _fixture("mastercard_foundation_institutions.json")

    monkeypatch.setattr(source_module, "get_html", fake_get_html)

    source = MastercardFoundationScholarsSource()
    results = await source.collect()

    open_records = [r for r in results if r.opportunity_status == "posted"]
    closed_records = [r for r in results if r.opportunity_status == "closed"]
    # Every record lands in exactly one bucket - never silently dropped
    # because its own current cycle happens to be closed.
    assert len(open_records) + len(closed_records) == len(results)
    assert open_records
    assert closed_records

    addis = next(r for r in results if "Addis Ababa University" in r.title)
    # The fixture's own application_window for this one is an empty
    # string, not "open"/"closed" - treated as the safe non-closed
    # default rather than guessed either way.
    assert addis.opportunity_status == "posted"
    assert "currently open" not in addis.description
    assert "currently closed" not in addis.description


@pytest.mark.asyncio
async def test_collect_returns_empty_list_when_fetch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_get_html(url: str, **_: object) -> str:
        raise ExternalAPIError("External page is temporarily unavailable.")

    monkeypatch.setattr(source_module, "get_html", failing_get_html)

    source = MastercardFoundationScholarsSource()
    results = await source.collect()

    assert results == []


@pytest.mark.asyncio
async def test_collect_returns_empty_list_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_html(url: str, **_: object) -> str:
        return "not json at all"

    monkeypatch.setattr(source_module, "get_html", fake_get_html)

    source = MastercardFoundationScholarsSource()
    results = await source.collect()

    assert results == []


@pytest.mark.asyncio
async def test_collect_returns_empty_list_on_unexpected_json_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirrors this project's standard graceful-degradation pattern for a

    site redesign - if the endpoint ever starts returning an object
    instead of a list, this must never crash the sync task.
    """

    async def fake_get_html(url: str, **_: object) -> str:
        return '{"institutions": []}'

    monkeypatch.setattr(source_module, "get_html", fake_get_html)

    source = MastercardFoundationScholarsSource()
    results = await source.collect()

    assert results == []
