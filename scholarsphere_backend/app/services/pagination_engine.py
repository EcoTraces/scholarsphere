"""Reusable pagination support for scraper sources, covering the three
shapes named in the spec:

- **Standard pagination** (a "Next" button, page 1 -> Next -> page 2 -> ...)
  and **JavaScript pagination** (a "Load More" button where the URL never
  changes) both go through `paginate_by_click`, which is deliberately
  shape-agnostic: a caller-supplied `extract_items()` reads whatever is
  currently in the DOM after each click - if a source *replaces* the
  listing (standard "Next"), that's this page's items; if a source
  *appends* to it ("Load More"), that's every item on the page so far.
  Either way, deduplication by `key_fn` means only genuinely new records
  ever get counted or appended to the result - the caller doesn't need to
  know or declare which shape a given source uses.
- **URL pagination** (`?page=1`, `?page=2`, ...) goes through
  `paginate_by_url`, which needs no browser at all - just an async
  `fetch_page(url) -> list[T]` callable (typically a thin wrapper around
  a source's own existing HTTP or browser-rendering fetch + parse step).

Every loop here stops on one of: no "next"/"load more" control found, that
control being disabled, a page/scroll yielding no genuinely new records,
`max_pages`/`max_records` being reached, or the underlying fetch failing -
never an unbounded loop, matching the spec's own "never blindly click
forever" rule. Defaults come from `app.core.config.Settings`
(`max_pages_per_source`/`max_records_per_source`) so every source shares
one configurable ceiling unless it explicitly overrides it.
"""

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

from urllib.parse import urlsplit

from app.core.config import get_settings
from app.services.scraper_metrics import get_metrics
from app.services.source_capability_profile import get_capability_registry

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class PaginationResult(Generic[T]):
    items: list[T]
    pages_visited: int
    #: "no_next_control" | "next_control_disabled" | "no_new_records" |
    #: "empty_page" | "max_pages_reached" | "max_records_reached" |
    #: "click_failed" | "fetch_failed"
    stopped_reason: str


async def paginate_by_url(
    fetch_page: Callable[[str], Awaitable[list[T]]],
    *,
    url_template: str,
    key_fn: Callable[[T], str],
    start_page: int = 1,
    max_pages: int | None = None,
    max_records: int | None = None,
) -> PaginationResult[T]:
    """`url_template` must contain a `{page}` placeholder, e.g.
    `"https://example.test/scholarships?page={page}"`. `fetch_page(url)`
    should return that page's extracted items (an empty list for "past
    the last page"), raising on a genuine fetch failure rather than
    returning an empty list for one - this stops on `empty_page` either
    way, but a raised exception is logged with the URL for diagnosis.
    """
    settings = get_settings()
    max_pages = max_pages or settings.max_pages_per_source
    max_records = max_records or settings.max_records_per_source

    items: list[T] = []
    seen_keys: set[str] = set()
    page_number = start_page
    pages_visited = 0
    stopped_reason = "max_pages_reached"

    for _ in range(max_pages):
        url = url_template.format(page=page_number)
        try:
            page_items = await fetch_page(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("pagination_fetch_failed url=%s error=%s", url, exc)
            stopped_reason = "fetch_failed"
            break
        pages_visited += 1

        if not page_items:
            stopped_reason = "empty_page"
            break

        new_items = [item for item in page_items if key_fn(item) not in seen_keys]
        if not new_items:
            stopped_reason = "no_new_records"
            break

        for item in new_items:
            seen_keys.add(key_fn(item))
            items.append(item)

        if len(items) >= max_records:
            items = items[:max_records]
            stopped_reason = "max_records_reached"
            break

        page_number += 1
    else:
        stopped_reason = "max_pages_reached"

    get_metrics().increment("pagination_pages", by=pages_visited)
    if pages_visited > 1:
        host = urlsplit(url_template.format(page=start_page)).hostname
        if host:
            get_capability_registry().record(host, pagination_type="url")
    return PaginationResult(
        items=items, pages_visited=pages_visited, stopped_reason=stopped_reason
    )


async def paginate_by_click(
    engine: object,
    *,
    extract_items: Callable[[], Awaitable[list[T]]],
    next_control_selector: str,
    key_fn: Callable[[T], str],
    max_pages: int | None = None,
    max_records: int | None = None,
) -> PaginationResult[T]:
    """`engine` is a `app.services.browser_interaction.
    BrowserInteractionEngine` already positioned on the listing's first
    page. `extract_items()` reads and returns whatever items are
    currently visible/loaded in the DOM (see this module's docstring for
    why that works for both "Next" and "Load More" shapes).
    `next_control_selector` is a CSS selector for the next/load-more
    control; a disabled control (`disabled` attribute/ARIA state) or one
    that's simply absent stops the loop.
    """
    settings = get_settings()
    max_pages = max_pages or settings.max_pages_per_source
    max_records = max_records or settings.max_records_per_source

    items: list[T] = []
    seen_keys: set[str] = set()
    pages_visited = 0
    stopped_reason = "max_pages_reached"

    for _ in range(max_pages):
        try:
            page_items = await extract_items()
        except Exception as exc:  # noqa: BLE001
            logger.warning("pagination_extract_failed error=%s", exc)
            stopped_reason = "fetch_failed"
            break
        pages_visited += 1

        new_items = [item for item in page_items if key_fn(item) not in seen_keys]
        for item in new_items:
            seen_keys.add(key_fn(item))
            items.append(item)

        if len(items) >= max_records:
            items = items[:max_records]
            stopped_reason = "max_records_reached"
            break

        if not new_items and pages_visited > 1:
            stopped_reason = "no_new_records"
            break

        next_locator = engine.page.locator(next_control_selector)  # type: ignore[attr-defined]
        if await next_locator.count() == 0:
            stopped_reason = "no_next_control"
            break
        try:
            if await next_locator.first.is_disabled():
                stopped_reason = "next_control_disabled"
                break
        except Exception:  # noqa: BLE001 - element without a meaningful disabled state
            pass

        try:
            await engine.mark_baseline()  # type: ignore[attr-defined]
            await next_locator.first.click(timeout=engine.default_timeout_ms)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            logger.info("pagination_click_failed error=%s", exc)
            stopped_reason = "click_failed"
            break
        await engine.wait_for_navigation_or_change()  # type: ignore[attr-defined]
    else:
        stopped_reason = "max_pages_reached"

    get_metrics().increment("pagination_pages", by=pages_visited)
    if pages_visited > 1:
        host = urlsplit(engine.page.url).hostname  # type: ignore[attr-defined]
        if host:
            get_capability_registry().record(host, pagination_type="click")
    return PaginationResult(
        items=items, pages_visited=pages_visited, stopped_reason=stopped_reason
    )
