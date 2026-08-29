"""Browser-rendering fallback for scraper sources whose pages don't return
usable content over plain HTTP - a JavaScript single-page app that only
populates its content client-side after load. Used only by
`app/services/web_scraper_base.py::WebScraperSource._fetch_html`, and only
for sources that opt in via `allow_browser_rendering = True` (see that
class), so every one of this project's existing HTTP-only sources is
completely unaffected.

Design, matching this project's existing HTTPS-only/never-fabricate/
never-bypass-protection discipline:

- HTTP remains the default and only path for every source unless it opts
  in - this module is never invoked speculatively "just in case."
- Same HTTPS-only rule as every other fetch in this codebase
  (`app.core.http_client.validate_https_url`) - no exceptions.
- One Chromium instance is launched lazily and reused across fetches
  (browser launch is the expensive part); each fetch gets its own fresh,
  isolated `BrowserContext` + `Page`, always closed in a `finally` block,
  never leaked across requests.
- A bounded semaphore caps how many renders can run concurrently
  (`settings.browser_render_max_concurrency`) so a burst of scheduled
  scraper tasks can't spawn unbounded browser pages.
- No fixed `sleep()`-based waits: navigation uses `wait_until=
  "domcontentloaded"` and an optional caller-supplied CSS selector via
  `page.wait_for_selector`, both under an explicit bounded timeout
  (`settings.browser_render_timeout_ms`).
- If the rendered page matches a known bot-challenge/CAPTCHA signature
  (Cloudflare's interstitial, hCaptcha/reCAPTCHA markers, a generic
  "access denied" page), this raises `ExternalAPIError` immediately -
  the same "never attempt to bypass, log and move on" policy already
  applied everywhere in this project (Cyprus's Azure WAF, Brazil's
  F5/Distil challenge, Israel's 403 - see docs/COUNTRY_PROVIDER_REGISTRY.md).
  It never solves a CAPTCHA, never fills in a form, never creates an
  account, and never submits anything - this module only ever reads a
  publicly reachable page and returns its rendered HTML.
- Rendered content is not treated as more trustworthy than plain HTML -
  it goes through the exact same downstream parsing/normalization
  (`WebScraperSource.fetch_soup`), the same mandatory-human-review gate,
  and the same real-fixture-based testing as every other source.
"""

import asyncio
import logging

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError, validate_https_url

logger = logging.getLogger(__name__)

# Substrings (checked case-insensitively against the rendered page's own
# text/title) that indicate an active bot-challenge or access-control wall
# rather than real content - never attempt to solve or route around any
# of these; treat the fetch as blocked, same as this project's policy for
# every previously-encountered anti-bot measure.
_CHALLENGE_MARKERS: tuple[str, ...] = (
    "checking your browser",
    "cf-browser-verification",
    "attention required! | cloudflare",
    "verify you are human",
    "please verify you are a human",
    "captcha",
    "hcaptcha",
    "recaptcha",
    "access denied",
    "request blocked",
)

_playwright_context = None
_browser = None
_semaphore = None


class BrowserRenderingUnavailable(ExternalAPIError):
    """Playwright itself, or a launchable browser, isn't available in this
    environment - raised instead of letting an ImportError or a browser
    launch failure propagate as a generic crash. Callers should treat this
    the same as any other `ExternalAPIError`: log it and move on to the
    next source, never crash the whole scheduled run.
    """


async def _get_browser():
    global _playwright_context, _browser, _semaphore
    if _browser is not None:
        return _browser

    settings = get_settings()
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.browser_render_max_concurrency)

    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise BrowserRenderingUnavailable(
            "Browser rendering is not available: the playwright package "
            "is not installed."
        ) from exc

    try:
        _playwright_context = await async_playwright().start()
        launch_kwargs: dict[str, object] = {"headless": True}
        if settings.browser_executable_path:
            launch_kwargs["executable_path"] = settings.browser_executable_path
        _browser = await _playwright_context.chromium.launch(**launch_kwargs)
    except Exception as exc:  # noqa: BLE001 - any launch failure is fatal here
        _playwright_context = None
        _browser = None
        raise BrowserRenderingUnavailable(
            "Browser rendering is not available: the browser failed to "
            "launch."
        ) from exc
    return _browser


async def shutdown_browser() -> None:
    """Closes the shared browser and its Playwright driver, if running.
    Safe to call even if rendering was never used. Intended for an app
    shutdown hook, not for use between individual fetches (the browser is
    deliberately reused across fetches - see this module's docstring).
    """
    global _playwright_context, _browser
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright_context is not None:
        await _playwright_context.stop()
        _playwright_context = None


def _looks_like_a_challenge_page(title: str, text: str) -> bool:
    haystack = f"{title}\n{text}".lower()
    return any(marker in haystack for marker in _CHALLENGE_MARKERS)


async def fetch_rendered_html(
    url: str,
    *,
    wait_for_selector: str | None = None,
    timeout_ms: int | None = None,
) -> str:
    """Renders `url` in a headless browser and returns the resulting HTML.

    Raises `ExternalAPIError` (or the `BrowserRenderingUnavailable`
    subclass, when the browser itself can't be started) on any failure -
    navigation timeout, a detected bot-challenge, or a response over the
    configured size limit - so callers can handle it exactly like a failed
    plain-HTTP fetch.
    """
    validate_https_url(url)
    settings = get_settings()
    effective_timeout = timeout_ms or settings.browser_render_timeout_ms

    browser = await _get_browser()
    assert _semaphore is not None  # set alongside the browser above

    async with _semaphore:
        context = await browser.new_context(
            user_agent=(
                "ScholarSphere/1.0 (+scholarship discovery; "
                "opportunities@scholarsphere.app)"
            ),
        )
        try:
            page = await context.new_page()
            try:
                await page.goto(
                    url, wait_until="domcontentloaded", timeout=effective_timeout
                )
                if wait_for_selector:
                    try:
                        await page.wait_for_selector(
                            wait_for_selector, timeout=effective_timeout
                        )
                    except Exception:  # noqa: BLE001
                        # The hinted selector never showed up - proceed with
                        # whatever rendered anyway rather than failing the
                        # whole fetch; the downstream parser's own missing-
                        # selector handling takes it from there.
                        logger.info(
                            "browser_render_selector_not_found url=%s selector=%s",
                            url,
                            wait_for_selector,
                        )
                html = await page.content()
                title = await page.title()
            except Exception as exc:  # noqa: BLE001
                raise ExternalAPIError(
                    "External page could not be rendered."
                ) from exc
        finally:
            await context.close()

    if len(html.encode("utf-8", errors="ignore")) > settings.http_max_response_bytes:
        raise ExternalAPIError("Rendered page response is too large.")

    if _looks_like_a_challenge_page(title, html[:20_000]):
        logger.warning("browser_render_blocked_by_challenge url=%s", url)
        raise ExternalAPIError(
            "External page is behind an active bot-challenge; not attempting "
            "to bypass it."
        )

    return html
