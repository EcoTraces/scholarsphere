"""Tests for app/services/pagination_engine.py.

`paginate_by_url` needs no browser at all - tested with a plain in-memory
fake `fetch_page`. `paginate_by_click` is tested against a real headless
Chromium in tests/test_browser_interaction_pagination.py (it needs a live
Playwright locator/click, so it belongs with the other real-browser
tests).
"""

import pytest

from app.services.pagination_engine import PaginationResult, paginate_by_url


@pytest.mark.asyncio
async def test_paginate_by_url_stops_on_empty_page() -> None:
    pages = {
        1: ["a", "b"],
        2: ["c", "d"],
        3: [],
    }

    async def fetch_page(url: str) -> list[str]:
        page_number = int(url.rsplit("=", 1)[1])
        return pages.get(page_number, [])

    result = await paginate_by_url(
        fetch_page,
        url_template="https://example.test/list?page={page}",
        key_fn=lambda item: item,
        max_pages=10,
        max_records=100,
    )

    assert result.items == ["a", "b", "c", "d"]
    assert result.pages_visited == 3
    assert result.stopped_reason == "empty_page"


@pytest.mark.asyncio
async def test_paginate_by_url_stops_on_max_pages() -> None:
    async def fetch_page(url: str) -> list[str]:
        page_number = int(url.rsplit("=", 1)[1])
        return [f"item-{page_number}"]

    result = await paginate_by_url(
        fetch_page,
        url_template="https://example.test/list?page={page}",
        key_fn=lambda item: item,
        max_pages=3,
        max_records=100,
    )

    assert result.pages_visited == 3
    assert result.stopped_reason == "max_pages_reached"
    assert len(result.items) == 3


@pytest.mark.asyncio
async def test_paginate_by_url_stops_on_max_records() -> None:
    async def fetch_page(url: str) -> list[str]:
        page_number = int(url.rsplit("=", 1)[1])
        return [f"item-{page_number}-{i}" for i in range(5)]

    result = await paginate_by_url(
        fetch_page,
        url_template="https://example.test/list?page={page}",
        key_fn=lambda item: item,
        max_pages=100,
        max_records=12,
    )

    assert len(result.items) == 12
    assert result.stopped_reason == "max_records_reached"


@pytest.mark.asyncio
async def test_paginate_by_url_never_loops_forever_on_a_repeated_page() -> None:
    """A misbehaving source that serves the exact same page for every
    `?page=N` must not spin - deduplication by key means the second page
    has zero *new* items, which stops the loop immediately.
    """

    async def fetch_page(url: str) -> list[str]:
        return ["same-item"]

    result = await paginate_by_url(
        fetch_page,
        url_template="https://example.test/list?page={page}",
        key_fn=lambda item: item,
        max_pages=1000,
        max_records=100_000,
    )

    assert result.items == ["same-item"]
    assert result.pages_visited == 2
    assert result.stopped_reason == "no_new_records"


@pytest.mark.asyncio
async def test_paginate_by_url_stops_on_fetch_failure() -> None:
    async def fetch_page(url: str) -> list[str]:
        raise RuntimeError("boom")

    result = await paginate_by_url(
        fetch_page,
        url_template="https://example.test/list?page={page}",
        key_fn=lambda item: item,
    )

    assert result.items == []
    assert result.pages_visited == 0
    assert result.stopped_reason == "fetch_failed"


@pytest.mark.asyncio
async def test_paginate_by_url_uses_configured_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import pagination_engine

    class _Settings:
        max_pages_per_source = 2
        max_records_per_source = 1000

    monkeypatch.setattr(pagination_engine, "get_settings", lambda: _Settings())

    async def fetch_page(url: str) -> list[str]:
        page_number = int(url.rsplit("=", 1)[1])
        return [f"item-{page_number}"]

    result = await paginate_by_url(
        fetch_page,
        url_template="https://example.test/list?page={page}",
        key_fn=lambda item: item,
    )

    assert result.pages_visited == 2
    assert result.stopped_reason == "max_pages_reached"


def test_pagination_result_is_a_plain_dataclass() -> None:
    result = PaginationResult(items=[1, 2], pages_visited=1, stopped_reason="empty_page")
    assert result.items == [1, 2]
