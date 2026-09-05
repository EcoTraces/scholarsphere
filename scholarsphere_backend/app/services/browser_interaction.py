"""Reusable SPA-interaction primitives on top of a live Playwright `Page`
opened via `app.services.browser_rendering.interactive_session`.

Built for scraper adapters (and the pagination/infinite-scroll/
application-link-discovery engines built on top of this) that need more
than a single render - clicking into a scholarship card, opening a detail
modal, following a client-side route change (a React/Vue-style app that
swaps content via `history.pushState` or DOM mutation instead of a full
page navigation). Every wait here races a real DOM/network condition
under a bounded timeout - never a fixed `sleep()`.

Uses selectors, Playwright's accessible-role locators, and plain text
matches - never brittle pixel/coordinate clicks.

Never used to submit a form, fill in input fields, or interact with
anything beyond reading rendered content and following ordinary
navigation/disclosure controls - see `app.services.browser_rendering`'s
module docstring for this project's standing never-submit/never-bypass
policy, which applies identically here. This engine only clicks, waits,
and reads; it has no method that accepts form field values.
"""

import asyncio
from dataclasses import dataclass


@dataclass
class ClickOutcome:
    """What happened after a `BrowserInteractionEngine.click()` call, as
    observed by `wait_for_navigation_or_change`.

    `kind` is one of:
      "new_tab"    - the click opened a new tab/popup (a `target="_blank"`
                     link, or `window.open`). `new_page` holds that tab's
                     Playwright `Page`.
      "url_change" - `window.location.href` changed, whether via a full
                     navigation or a client-side `history.pushState`
                     route change.
      "dom_change" - the URL didn't change, but the page's own rendered
                     DOM did (a modal opened, an accordion expanded, a
                     card's detail view swapped in without changing the
                     route).
      "no_change"  - nothing observably changed within the timeout - the
                     click may have been a no-op, or the resulting change
                     was slower than the caller's timeout allows.
    """

    kind: str
    url: str | None
    new_page: object | None = None


class BrowserInteractionEngine:
    """Wraps one live Playwright `Page`. Typically constructed from
    `app.services.browser_rendering.interactive_session`:

        async with interactive_session(url) as page:
            engine = BrowserInteractionEngine(page)
            await engine.click("text=View details")
            outcome = await engine.wait_for_navigation_or_change()
            html = await engine.capture_rendered_content()
    """

    def __init__(self, page: object, *, default_timeout_ms: int = 10_000) -> None:
        self._page = page
        self._default_timeout_ms = default_timeout_ms
        # Captured by `click()` right before the actual click, so
        # `wait_for_navigation_or_change()` compares against the state
        # that existed *before* the click's own (often synchronous) JS
        # handler ran - not the state after it, which would make every
        # change invisible to the race below.
        self._pending_baseline: tuple[str, int] | None = None

    @property
    def page(self) -> object:
        return self._page

    @property
    def default_timeout_ms(self) -> int:
        return self._default_timeout_ms

    def extract_current_url(self) -> str:
        return self._page.url  # type: ignore[attr-defined]

    async def capture_rendered_content(self) -> str:
        return await self._page.content()  # type: ignore[attr-defined]

    async def wait_for_selector(
        self, selector: str, *, timeout_ms: int | None = None
    ) -> None:
        await self._page.wait_for_selector(  # type: ignore[attr-defined]
            selector, timeout=timeout_ms or self._default_timeout_ms
        )

    def _locator(
        self,
        selector: str,
        *,
        by: str,
        text: str | None,
    ) -> object:
        page = self._page
        if by == "role":
            return page.get_by_role(selector, name=text)  # type: ignore[attr-defined]
        if by == "text":
            return page.get_by_text(text or selector)  # type: ignore[attr-defined]
        return page.locator(selector)  # type: ignore[attr-defined]

    async def mark_baseline(self) -> None:
        """Snapshots the current URL and rendered-DOM length so a
        subsequent `wait_for_navigation_or_change()` call can detect a
        real change even when the trigger wasn't `click()` itself (e.g. a
        caller driving a raw Playwright locator directly - see
        app.services.application_link_discovery). `click()` calls this
        internally; a caller only needs to call it directly when clicking
        through some other means.
        """
        self._pending_baseline = (
            self._page.url,  # type: ignore[attr-defined]
            len(await self._page.content()),  # type: ignore[attr-defined]
        )

    async def click(
        self,
        selector: str,
        *,
        by: str = "selector",
        text: str | None = None,
        nth: int = 0,
        timeout_ms: int | None = None,
    ) -> None:
        """Clicks the `nth` (default: first) match of `selector`.

        `by` picks the locator strategy:
          "selector" (default) - a CSS selector, via `page.locator`.
          "role"    - an accessible role (e.g. "button", "link"); pass the
                      role as `selector` and the accessible name to match
                      as `text`.
          "text"    - a plain visible-text match, via `page.get_by_text`.
        """
        timeout = timeout_ms or self._default_timeout_ms
        locator = self._locator(selector, by=by, text=text)
        # Snapshot state *before* the click - its own onclick handler
        # typically runs synchronously, often completing before this
        # await even returns, so this must happen first, not inside
        # `wait_for_navigation_or_change`.
        await self.mark_baseline()
        await locator.nth(nth).click(timeout=timeout)  # type: ignore[attr-defined]

    async def wait_for_navigation_or_change(
        self, *, timeout_ms: int | None = None
    ) -> ClickOutcome:
        """Call immediately after `click()`. Races three real, observable
        outcomes - a new tab opening, `window.location.href` changing, or
        the page's own rendered DOM changing without a URL change - and
        returns as soon as the first one happens, or `"no_change"` if
        none happen within the timeout. Never sleeps a fixed duration.

        Compares against the state captured by the preceding `click()`
        call when one was made (see `_pending_baseline`); falls back to
        capturing fresh state now for a caller using this after some
        other trigger (e.g. a programmatic `page.goto` elsewhere).
        """
        timeout = timeout_ms or self._default_timeout_ms
        page = self._page
        context = page.context  # type: ignore[attr-defined]
        if self._pending_baseline is not None:
            before_url, before_html_len = self._pending_baseline
            self._pending_baseline = None
        else:
            before_url = page.url  # type: ignore[attr-defined]
            before_html_len = len(await page.content())  # type: ignore[attr-defined]

        async def _wait_new_tab() -> object:
            return await context.wait_for_event("page", timeout=timeout)

        async def _wait_url_change() -> None:
            await page.wait_for_function(
                "(before) => window.location.href !== before",
                arg=before_url,
                timeout=timeout,
            )

        async def _wait_dom_change() -> None:
            await page.wait_for_function(
                "(before) => document.documentElement.outerHTML.length !== before",
                arg=before_html_len,
                timeout=timeout,
            )

        tasks: dict[asyncio.Task, str] = {
            asyncio.ensure_future(_wait_new_tab()): "new_tab",
            asyncio.ensure_future(_wait_url_change()): "url_change",
            asyncio.ensure_future(_wait_dom_change()): "dom_change",
        }

        kind = "no_change"
        result_url = page.url  # type: ignore[attr-defined]
        new_page: object | None = None
        try:
            done, _pending = await asyncio.wait(
                tasks.keys(),
                timeout=(timeout / 1000) + 1,
                return_when=asyncio.FIRST_COMPLETED,
            )
            succeeded = [t for t in done if t.exception() is None]
            if succeeded:
                winner = succeeded[0]
                kind = tasks[winner]
                if kind == "new_tab":
                    new_page = winner.result()
                    try:
                        await new_page.wait_for_load_state(  # type: ignore[attr-defined]
                            "domcontentloaded", timeout=timeout
                        )
                    except Exception:  # noqa: BLE001 - best-effort only
                        pass
                    result_url = new_page.url  # type: ignore[attr-defined]
                else:
                    result_url = page.url  # type: ignore[attr-defined]
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks.keys(), return_exceptions=True)

        return ClickOutcome(kind=kind, url=result_url, new_page=new_page)
