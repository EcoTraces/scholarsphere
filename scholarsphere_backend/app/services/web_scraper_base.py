"""Shared fetch/parse infrastructure for HTML-scraper opportunity sources.

Used only for organizations with no official API, RSS feed, or dataset -
see docs/AUTHORITATIVE_SOURCES.md for the per-source research (official
domain confirmation, robots.txt check, page-structure verification against
real fetched HTML) performed before each source below was added. Every
subclass of `WebScraperSource`:

- fetches over HTTPS only, with the same timeout/retry/response-size limits
  every API source gets (`app/core/http_client.py::get_html`);
- waits at least `min_request_interval_seconds` between requests to the
  same host within this process, to stay comfortably under any published
  robots.txt crawl-delay;
- never invents a field - a value not actually present on the page is left
  `None`, never guessed, inferred, or AI-generated (see
  docs/OPPORTUNITY_VERIFICATION_SYSTEM.md SS10, "AI's role: none, today" -
  that remains true here, this is deterministic tag/text extraction);
- still lands every record as `verification_status=pending`,
  `publication_status=unpublished` - enforced by
  `NormalizedExternalOpportunity` itself, not by adapter discipline - so a
  scraped record is never auto-published; a human verification officer
  always reviews it before it can go live (see
  docs/OPPORTUNITY_VERIFICATION_SYSTEM.md).
"""

import asyncio
import logging
from time import monotonic
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from app.core.http_client import get_html
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.base_source import OpportunitySource

logger = logging.getLogger(__name__)

_last_request_at: dict[str, float] = {}
_host_locks: dict[str, asyncio.Lock] = {}

#: Phrases a JavaScript app's static shell commonly leaves behind for a
#: client that doesn't execute it - checked case-insensitively.
_JS_SHELL_MARKERS: tuple[str, ...] = (
    "you need to enable javascript",
    "please enable javascript",
    "javascript is required",
    "loading...",
    "loading homepage",
)
#: Below this many characters of real body text, a page is treated as an
#: unrendered JS shell rather than a genuinely thin (but real) page -
#: chosen well under every real source's own thinnest confirmed real page
#: in this project (Colombia ICETEX's reciprocity page, ~330 characters)
#: so a legitimately thin page is never misclassified as JS-only.
_MIN_REAL_CONTENT_CHARS = 150


def looks_javascript_rendered(html: str) -> bool:
    """True if `html` (a plain-HTTP response) looks like a JavaScript
    single-page app's unrendered shell rather than real content - used by
    `WebScraperSource._fetch_html` to decide whether to fall back to
    `app.services.browser_rendering` for a source that opts in via
    `allow_browser_rendering`. Deliberately conservative: only flags a
    page when its own body text is very thin AND either an explicit
    "enable JavaScript"-style marker is present or there's essentially no
    text at all - a real, if thin, page like Colombia ICETEX's 330-
    character reciprocity page must never trigger this.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    if len(text) >= _MIN_REAL_CONTENT_CHARS:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in _JS_SHELL_MARKERS):
        return True
    return len(text) == 0


def _lock_for(host: str) -> asyncio.Lock:
    lock = _host_locks.get(host)
    if lock is None:
        lock = asyncio.Lock()
        _host_locks[host] = lock
    return lock


class WebScraperSource(OpportunitySource):
    """Base class for `OpportunitySource` implementations that scrape HTML
    instead of calling a structured API.
    """

    #: Minimum seconds between two requests to the same host from this
    #: process. Defaults to the most conservative published crawl-delay
    #: among the sites currently integrated (DAAD: 2s); subclasses may
    #: raise this but should not lower it below a site's own robots.txt.
    min_request_interval_seconds: float = 2.0

    #: Opt-in only - see app/services/browser_rendering.py's module
    #: docstring. When True, a plain-HTTP fetch that
    #: `looks_javascript_rendered` flags as an unrendered JS shell is
    #: retried once through a headless browser. Every existing source
    #: leaves this False and is completely unaffected; a source only
    #: needs it when its own live-testing (documented in
    #: docs/AUTHORITATIVE_SOURCES.md, same as every other design choice)
    #: showed the plain-HTTP response really is a JS-only shell.
    allow_browser_rendering: bool = False
    #: Optional CSS selector to wait for when browser-rendering this
    #: source's pages, so the render doesn't return before the page's own
    #: async content has actually loaded. `None` waits only for
    #: `domcontentloaded`.
    browser_wait_for_selector: str | None = None

    async def collect_for_import(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[NormalizedExternalOpportunity | dict[str, Any]]:
        """Scrapers validate/skip per-item defensively inside `collect()`
        rather than via a separate malformed-payload path, so this is the
        same as `collect()` - kept as a distinct method to match the
        interface `app/tasks/opportunity_sync.py::_run_source_sync` calls
        on every source.
        """
        return await self.collect(keyword=keyword, page=page, page_size=page_size)

    async def fetch_soup(self, url: str) -> BeautifulSoup:
        html = await self._fetch_html(url)
        return BeautifulSoup(html, "html.parser")

    async def _fetch_html(self, url: str) -> str:
        host = urlsplit(url).hostname or ""
        async with _lock_for(host):
            last = _last_request_at.get(host)
            if last is not None:
                wait = self.min_request_interval_seconds - (monotonic() - last)
                if wait > 0:
                    await asyncio.sleep(wait)
            try:
                html = await get_html(url)
            finally:
                _last_request_at[host] = monotonic()

        if self.allow_browser_rendering and looks_javascript_rendered(html):
            html = await self._fetch_rendered_html(url, fallback=html)
        return html

    async def _fetch_rendered_html(self, url: str, *, fallback: str) -> str:
        # Imported lazily so every source that never opts into browser
        # rendering (i.e. every source today) never even imports
        # playwright, let alone requires it to be installed.
        from app.services.browser_rendering import fetch_rendered_html

        try:
            return await fetch_rendered_html(
                url, wait_for_selector=self.browser_wait_for_selector
            )
        except Exception as exc:  # noqa: BLE001
            # Never let a browser-rendering failure crash this source's
            # sync task (and, with it, every other source scheduled
            # alongside it) - fall back to the thin HTTP response, which
            # this source's own downstream parsing already handles
            # gracefully (a missing selector yields a safe default, not a
            # crash - see tests/test_scraper_resilience.py).
            logger.warning(
                "browser_render_failed_falling_back_to_http url=%s error=%s",
                url,
                exc,
            )
            return fallback


def absolute_https_url(base: str, href: str | None) -> str | None:
    """Resolve `href` against `base` and return it only if the result is a
    well-formed HTTPS URL - matches the HTTPS-only rule every other source
    already enforces (`NormalizedExternalOpportunity.https_urls_only`).

    Deliberately does NOT restrict the result to `base`'s own host - some
    callers (e.g. an official source page linking out to a distinct
    official application portal) legitimately need a different host. Use
    `same_host_https_url` instead when a caller discovers links to follow
    and fetch (not just to record) - see its docstring for why that
    distinction matters.
    """
    if not href or not href.strip():
        return None
    resolved = urljoin(base, href.strip())
    parts = urlsplit(resolved)
    if parts.scheme != "https" or not parts.hostname:
        return None
    return resolved


def same_host_https_url(base: str, href: str | None) -> str | None:
    """Like `absolute_https_url`, but additionally rejects any result
    whose host doesn't match `base`'s host.

    Use this specifically when a link *discovered on a scraped page* will
    itself be fetched next (following a "next article" or "programme
    detail" link, for example) - without this check, a page under this
    adapter's own configured, trusted domain could still contain a link
    to an arbitrary third-party HTTPS host (an ad, a compromised/injected
    link, a redirect trick), and naive discovery would follow it,
    fetching attacker-influenced URLs under cover of a "trusted" source.
    Every source's fetch target must stay within the single domain that
    was actually vetted (see docs/AUTHORITATIVE_SOURCES.md's per-source
    robots.txt/terms research) - not wherever an arbitrary page happens to
    link.
    """
    resolved = absolute_https_url(base, href)
    if resolved is None:
        return None
    if urlsplit(resolved).hostname != urlsplit(base).hostname:
        return None
    return resolved


def clean_text(node: Tag | str | None) -> str | None:
    """Extract normalized whitespace-collapsed text from a BeautifulSoup
    node (or pass a plain string through), returning None for anything
    empty - never an empty string, so callers can rely on `or None`
    semantics matching the rest of the normalization layer.
    """
    if node is None:
        return None
    text = node.get_text(" ", strip=True) if isinstance(node, Tag) else str(node).strip()
    return text or None
