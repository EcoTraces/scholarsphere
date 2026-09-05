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
  "domcontentloaded"`, an optional caller-supplied CSS selector via
  `page.wait_for_selector`, and cookie-banner detection via a bounded
  `wait_for(state="visible")` - every wait races against a real DOM/
  network condition under an explicit timeout, never a fixed delay.
- Headless is the default and the only supported mode in production
  (`settings.browser_render_headless`, forced true whenever
  `app_env=production` - see app/core/config.py); a developer can flip
  `PLAYWRIGHT_HEADLESS=false` locally to watch a specific render happen.
- If the rendered page matches a known bot-challenge/CAPTCHA signature
  (Cloudflare's interstitial, hCaptcha/reCAPTCHA markers, a generic
  "access denied" page), this raises `ExternalAPIError` immediately -
  the same "never attempt to bypass, log and move on" policy already
  applied everywhere in this project (Cyprus's Azure WAF, Brazil's
  F5/Distil challenge, Israel's 403 - see docs/COUNTRY_PROVIDER_REGISTRY.md).
  It never solves a CAPTCHA, never fills in a form, never creates an
  account, and never submits anything - this module only ever reads a
  publicly reachable page (optionally dismissing a cookie/consent banner
  blocking that content - see `_maybe_accept_cookie_banner`) and returns
  its rendered HTML.
- Console errors, uncaught page exceptions, failed requests, and HTTP
  error responses observed during the render are captured as structured
  `PageEvent`s and classified INFO/WARNING/ERROR/CRITICAL (see
  `_classify_console_text`) rather than either silently discarded or used
  to blindly fail the whole render - a page's own third-party analytics
  tag throwing an error is not the same signal as its own scholarship-data
  endpoint returning HTTP 500.
- Rendered content is not treated as more trustworthy than plain HTML -
  it goes through the exact same downstream parsing/normalization
  (`WebScraperSource.fetch_soup`), the same mandatory-human-review gate,
  and the same real-fixture-based testing as every other source.
"""

import asyncio
import logging
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator
from urllib.parse import urlsplit

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError, validate_https_url
from app.services.scraper_metrics import get_metrics
from app.services.source_capability_profile import get_capability_registry

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

# Substrings that mark a console error/failed request as a harmless
# third-party script (analytics, ads, error-tracking beacons, ad-blocker
# interference) rather than a real problem with the page's own content -
# used so a source is never wrongly flagged just because, say, Google
# Analytics failed to load. Not exhaustive; anything not matched here
# defaults to a real (ERROR-severity) finding, which is the safer default.
_HARMLESS_CONSOLE_MARKERS: tuple[str, ...] = (
    "google-analytics",
    "googletagmanager",
    "gtag(",
    "doubleclick",
    "facebook.net",
    "connect.facebook",
    "hotjar",
    "sentry.io",
    "err_blocked_by_client",
    "err_aborted",
    "adsbygoogle",
    "googlesyndication",
)

# A cookie/consent banner's own container - deliberately scoped to
# elements whose id/class actually names "cookie"/"consent"/"gdpr", so the
# accept-button search below only ever looks inside a real consent banner,
# never at an arbitrary "Continue"/"Accept" button elsewhere on the page.
_COOKIE_CONTAINER_SELECTOR = (
    "[id*='cookie' i], [class*='cookie' i], "
    "[id*='consent' i], [class*='consent' i], "
    "[id*='gdpr' i], [class*='gdpr' i]"
)
# Matched only within a detected cookie/consent container (see above) -
# these are the "required to access content" accept actions from the
# spec's own examples, never a marketing/tracking opt-in checkbox.
_COOKIE_ACCEPT_TEXT_PATTERN = re.compile(
    r"^(accept(\s+all)?(\s+cookies)?|allow\s+cookies|i\s+agree|agree|"
    r"necessary\s+cookies(\s+only)?|continue)$",
    re.IGNORECASE,
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


@dataclass
class PageEvent:
    """One structured observation captured while rendering a page.

    `type` is one of "console_error", "console_warning", "page_error"
    (an uncaught JS exception in the page's own script), "network_failure"
    (a request that never got a response), or "http_error" (a response
    with a 4xx/5xx status). `severity` is one of "INFO", "WARNING",
    "ERROR", "CRITICAL" - see `_classify_console_text` and
    `_classify_response` for how each is assigned.
    """

    type: str
    severity: str
    message: str
    url: str


@dataclass
class RenderResult:
    """Everything observed while rendering one page - the HTML itself plus
    diagnostics. `fetch_rendered_html` (below) is a thin wrapper that
    returns just `.html`, for callers that only need the content; anything
    that also cares about what happened during the render (metrics,
    interactive engines) should call `render_page` directly.
    """

    html: str
    title: str
    final_url: str
    events: list[PageEvent] = field(default_factory=list)
    cookie_banner_detected: bool = False
    cookie_banner_handled: bool = False


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
        launch_kwargs: dict[str, object] = {
            "headless": settings.browser_render_headless
        }
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


def _classify_console_text(text: str) -> str:
    """ERROR by default (the safer assumption); downgraded to INFO only
    for a known-harmless third-party script/beacon/ad-blocker signature.
    """
    lowered = text.lower()
    if any(marker in lowered for marker in _HARMLESS_CONSOLE_MARKERS):
        return "INFO"
    return "ERROR"


def _classify_response_status(status: int, *, same_origin: bool) -> str:
    """A same-origin 5xx (the page's own backend/API failing) is the
    strongest real-failure signal this module can observe short of a
    completely blank page, so it's CRITICAL. A same-origin 4xx is
    ERROR-worthy but often just a missing asset. Third-party responses
    (ads, trackers, CDNs the page doesn't control) are downgraded a level
    either way - a third party being down is not this source's fault.
    """
    if status >= 500:
        return "CRITICAL" if same_origin else "WARNING"
    return "ERROR" if same_origin else "INFO"


async def _maybe_accept_cookie_banner(page, settings) -> tuple[bool, bool]:
    """Detects a cookie/consent banner blocking page content and, if
    `settings.browser_auto_accept_required_cookies` is true, clicks its
    accept control. Returns `(detected, handled)`. Never clicks anything
    outside a detected cookie/consent container (see
    `_COOKIE_CONTAINER_SELECTOR`), and never fills in a form or clicks a
    "reject"/"manage preferences" control - only a plain accept action, so
    public page content becomes visible.
    """
    short_timeout = min(2_000, settings.browser_render_timeout_ms)
    try:
        container = page.locator(_COOKIE_CONTAINER_SELECTOR).first
        await container.wait_for(state="visible", timeout=short_timeout)
    except Exception:  # noqa: BLE001 - no banner is the overwhelmingly common case
        return False, False

    if not settings.browser_auto_accept_required_cookies:
        return True, False

    for locator_factory in (
        lambda: container.get_by_role("button", name=_COOKIE_ACCEPT_TEXT_PATTERN),
        lambda: container.locator("button, a").filter(
            has_text=_COOKIE_ACCEPT_TEXT_PATTERN
        ),
    ):
        try:
            control = locator_factory().first
            await control.click(timeout=short_timeout)
            return True, True
        except Exception:  # noqa: BLE001 - try the next strategy, or give up
            continue
    return True, False


async def render_page(
    url: str,
    *,
    wait_for_selector: str | None = None,
    timeout_ms: int | None = None,
) -> RenderResult:
    """Renders `url` in a headless browser and returns the resulting HTML
    plus render diagnostics (`RenderResult`).

    Raises `ExternalAPIError` (or the `BrowserRenderingUnavailable`
    subclass, when the browser itself can't be started) on any failure -
    navigation timeout, a detected bot-challenge, or a response over the
    configured size limit - so callers can handle it exactly like a failed
    plain-HTTP fetch.
    """
    validate_https_url(url)
    settings = get_settings()
    metrics = get_metrics()
    effective_timeout = timeout_ms or settings.browser_render_timeout_ms
    target_host = urlsplit(url).hostname

    browser = await _get_browser()
    assert _semaphore is not None  # set alongside the browser above

    # Only imported after `_get_browser()` succeeds, so a genuinely
    # missing `playwright` package still surfaces as
    # `BrowserRenderingUnavailable` from `_get_browser()` itself, not a
    # raw ImportError from this line.
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    events: list[PageEvent] = []

    async with _semaphore:
        context = await browser.new_context(
            user_agent=(
                "ScholarSphere/1.0 (+scholarship discovery; "
                "opportunities@scholarsphere.app)"
            ),
        )
        try:
            page = await context.new_page()

            def _on_console(msg: object) -> None:
                msg_type = getattr(msg, "type", "")
                if msg_type not in ("error", "warning"):
                    return
                text = str(getattr(msg, "text", ""))[:500]
                severity = (
                    "WARNING" if msg_type == "warning" else _classify_console_text(text)
                )
                events.append(
                    PageEvent(
                        type=f"console_{msg_type}",
                        severity=severity,
                        message=text,
                        url=page.url,
                    )
                )

            def _on_pageerror(exc: object) -> None:
                events.append(
                    PageEvent(
                        type="page_error",
                        severity="ERROR",
                        message=str(exc)[:500],
                        url=page.url,
                    )
                )

            def _on_response(response: object) -> None:
                status = getattr(response, "status", 0)
                if status < 400:
                    return
                resp_url = getattr(response, "url", "")
                same_origin = urlsplit(resp_url).hostname == target_host
                events.append(
                    PageEvent(
                        type="http_error",
                        severity=_classify_response_status(
                            status, same_origin=same_origin
                        ),
                        message=f"HTTP {status}",
                        url=resp_url,
                    )
                )

            def _on_requestfailed(request: object) -> None:
                req_url = getattr(request, "url", "")
                failure = getattr(request, "failure", None) or "request failed"
                same_origin = urlsplit(req_url).hostname == target_host
                severity = _classify_console_text(str(failure))
                if severity != "INFO" and not same_origin:
                    severity = "WARNING"
                events.append(
                    PageEvent(
                        type="network_failure",
                        severity=severity,
                        message=str(failure)[:500],
                        url=req_url,
                    )
                )

            page.on("console", _on_console)
            page.on("pageerror", _on_pageerror)
            page.on("response", _on_response)
            page.on("requestfailed", _on_requestfailed)

            cookie_detected = cookie_handled = False
            try:
                await page.goto(
                    url, wait_until="domcontentloaded", timeout=effective_timeout
                )
                cookie_detected, cookie_handled = await _maybe_accept_cookie_banner(
                    page, settings
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
                final_url = page.url
            except PlaywrightTimeoutError as exc:
                metrics.increment("timeouts")
                raise ExternalAPIError(
                    "External page could not be rendered."
                ) from exc
            except Exception as exc:  # noqa: BLE001
                metrics.increment("network_failures")
                raise ExternalAPIError(
                    "External page could not be rendered."
                ) from exc
        finally:
            await context.close()

    if len(html.encode("utf-8", errors="ignore")) > settings.http_max_response_bytes:
        raise ExternalAPIError("Rendered page response is too large.")

    if _looks_like_a_challenge_page(title, html[:20_000]):
        metrics.increment("captcha_blocks")
        if target_host:
            get_capability_registry().record(target_host, blocked=True)
        logger.warning("browser_render_blocked_by_challenge url=%s", url)
        raise ExternalAPIError(
            "External page is behind an active bot-challenge; not attempting "
            "to bypass it."
        )

    if cookie_detected:
        metrics.increment("cookie_banners_detected")
        if target_host:
            get_capability_registry().record(target_host, cookie_banner=True)
        if cookie_handled:
            metrics.increment("cookie_banners_handled")

    real_error_events = [e for e in events if e.severity in ("ERROR", "CRITICAL")]
    console_error_count = sum(
        1 for e in real_error_events if e.type in ("console_error", "page_error")
    )
    network_error_count = sum(
        1
        for e in real_error_events
        if e.type in ("network_failure", "http_error")
    )
    if console_error_count:
        metrics.increment("console_errors", by=console_error_count)
    if network_error_count:
        metrics.increment("network_failures", by=network_error_count)

    return RenderResult(
        html=html,
        title=title,
        final_url=final_url,
        events=events,
        cookie_banner_detected=cookie_detected,
        cookie_banner_handled=cookie_handled,
    )


async def fetch_rendered_html(
    url: str,
    *,
    wait_for_selector: str | None = None,
    timeout_ms: int | None = None,
) -> str:
    """Thin wrapper around `render_page` for callers that only need the
    rendered HTML, not the full diagnostics - see `RenderResult`.
    """
    result = await render_page(
        url, wait_for_selector=wait_for_selector, timeout_ms=timeout_ms
    )
    return result.html


@asynccontextmanager
async def interactive_session(
    url: str, *, timeout_ms: int | None = None
) -> AsyncIterator[object]:
    """Opens `url` in a fresh, isolated `BrowserContext`/`Page` (same
    reused-browser/bounded-semaphore/HTTPS-only/cookie-banner-handling
    machinery as `render_page`) and yields the live Playwright `Page` for
    a caller that needs to keep interacting with it - clicking, waiting
    for a client-side route change, paging through results - rather than
    just reading one rendered snapshot.

    Used by `app.services.browser_interaction.BrowserInteractionEngine`
    and, through it, the pagination/infinite-scroll/application-link-
    discovery engines. Always closes the context on exit, even if the
    caller's block raises.
    """
    validate_https_url(url)
    settings = get_settings()
    metrics = get_metrics()
    effective_timeout = timeout_ms or settings.browser_render_timeout_ms
    target_host = urlsplit(url).hostname

    browser = await _get_browser()
    assert _semaphore is not None  # set alongside the browser above

    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

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
            except PlaywrightTimeoutError as exc:
                metrics.increment("timeouts")
                raise ExternalAPIError(
                    "External page could not be rendered."
                ) from exc
            except Exception as exc:  # noqa: BLE001
                metrics.increment("network_failures")
                raise ExternalAPIError(
                    "External page could not be rendered."
                ) from exc

            title = await page.title()
            html = await page.content()
            if _looks_like_a_challenge_page(title, html[:20_000]):
                metrics.increment("captcha_blocks")
                if target_host:
                    get_capability_registry().record(target_host, blocked=True)
                logger.warning("browser_render_blocked_by_challenge url=%s", url)
                raise ExternalAPIError(
                    "External page is behind an active bot-challenge; not "
                    "attempting to bypass it."
                )

            cookie_detected, cookie_handled = await _maybe_accept_cookie_banner(
                page, settings
            )
            if cookie_detected:
                metrics.increment("cookie_banners_detected")
                if target_host:
                    get_capability_registry().record(target_host, cookie_banner=True)
                if cookie_handled:
                    metrics.increment("cookie_banners_handled")

            yield page
        finally:
            await context.close()
