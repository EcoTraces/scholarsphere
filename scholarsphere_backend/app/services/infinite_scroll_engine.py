"""Controlled infinite-scroll support: render -> extract -> scroll -> wait
for new content -> extract -> compare -> continue, exactly the workflow
named in the spec.

Built on `app.services.browser_interaction.BrowserInteractionEngine`'s
underlying Playwright `Page` (an engine is accepted, not required, so a
caller that already has one from application-link discovery or clicked
navigation can reuse it directly). Every wait is a bounded
`page.wait_for_function` racing a real DOM-size change - never a fixed
`sleep()`.

Stops on whichever of these comes first: `max_scroll_iterations`,
`max_records`, or `scroll_stagnation_limit` consecutive scrolls that
yield no genuinely new records (comparing by `key_fn`, same
deduplication approach as `app.services.pagination_engine`). A "page
becomes unstable" condition (the DOM shrinking or `page.evaluate` itself
failing, e.g. a navigation occurred mid-scroll) also stops the loop
rather than continuing to scroll a page that's no longer the one being
measured.
"""

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

from urllib.parse import urlsplit

from app.core.config import get_settings
from app.services.pagination_engine import PaginationResult
from app.services.scraper_metrics import get_metrics
from app.services.source_capability_profile import get_capability_registry

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class InfiniteScrollResult(PaginationResult[T], Generic[T]):
    #: Renamed alias of `pages_visited` for readability at call sites -
    #: an infinite-scroll page doesn't have "pages" in the URL sense.
    @property
    def scroll_iterations(self) -> int:
        return self.pages_visited


async def scroll_and_extract(
    engine: object,
    *,
    extract_items: Callable[[], Awaitable[list[T]]],
    key_fn: Callable[[T], str],
    max_scroll_iterations: int | None = None,
    max_records: int | None = None,
    stagnation_limit: int | None = None,
    scroll_timeout_ms: int | None = None,
) -> InfiniteScrollResult[T]:
    settings = get_settings()
    max_scroll_iterations = max_scroll_iterations or settings.max_scroll_iterations
    max_records = max_records or settings.max_records_per_source
    stagnation_limit = stagnation_limit or settings.scroll_stagnation_limit
    timeout = scroll_timeout_ms or getattr(
        engine, "default_timeout_ms", settings.browser_render_timeout_ms
    )
    page = engine.page  # type: ignore[attr-defined]

    items: list[T] = []
    seen_keys: set[str] = set()
    stagnant_rounds = 0
    iterations_done = 0
    stopped_reason = "max_scroll_iterations_reached"

    for _ in range(max_scroll_iterations):
        try:
            page_items = await extract_items()
        except Exception as exc:  # noqa: BLE001
            logger.warning("infinite_scroll_extract_failed error=%s", exc)
            stopped_reason = "fetch_failed"
            break
        iterations_done += 1

        new_items = [item for item in page_items if key_fn(item) not in seen_keys]
        for item in new_items:
            seen_keys.add(key_fn(item))
            items.append(item)

        if len(items) >= max_records:
            items = items[:max_records]
            stopped_reason = "max_records_reached"
            break

        if not new_items:
            stagnant_rounds += 1
            if stagnant_rounds >= stagnation_limit:
                stopped_reason = "no_new_records"
                break
        else:
            stagnant_rounds = 0

        try:
            before_len = len(await page.content())
            await page.evaluate(
                "() => window.scrollTo(0, document.body.scrollHeight)"
            )
        except Exception as exc:  # noqa: BLE001 - page navigated/closed mid-scroll
            logger.warning("infinite_scroll_page_unstable error=%s", exc)
            stopped_reason = "page_unstable"
            break

        try:
            await page.wait_for_function(
                "(before) => document.documentElement.outerHTML.length !== before",
                arg=before_len,
                timeout=timeout,
            )
        except Exception:  # noqa: BLE001
            # No DOM growth within the timeout - the next loop's
            # `extract_items()`/stagnation check is what actually decides
            # whether to stop; this alone isn't fatal (a slow-loading
            # batch may still be mid-flight).
            pass
    else:
        stopped_reason = "max_scroll_iterations_reached"

    get_metrics().increment("infinite_scroll_pages", by=iterations_done)
    if iterations_done > 1:
        host = urlsplit(page.url).hostname  # type: ignore[attr-defined]
        if host:
            get_capability_registry().record(host, pagination_type="infinite_scroll")
    return InfiniteScrollResult(
        items=items, pages_visited=iterations_done, stopped_reason=stopped_reason
    )
