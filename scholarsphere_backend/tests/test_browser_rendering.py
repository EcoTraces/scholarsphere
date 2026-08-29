"""Tests for the browser-rendering fallback
(app/services/browser_rendering.py and web_scraper_base.py's
`looks_javascript_rendered` heuristic / `WebScraperSource` wiring).

The heuristic and wiring tests use only fixture strings and mocks, like
every other test in this suite. The `TestFetchRenderedHtml` tests below
launch a real headless Chromium against a local, self-signed-HTTPS test
server (127.0.0.1, never leaving the machine) - a genuine end-to-end
proof that rendering, selector-waiting, size-limiting, and challenge-page
detection all actually work, not just that the wiring calls the right
mock. They skip cleanly (not fail) when Playwright's browser isn't
installed in the current environment, so they don't block CI/dev setups
that haven't run `playwright install chromium`.
"""

import asyncio
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from app.core.http_client import ExternalAPIError
from app.services import browser_rendering, web_scraper_base
from app.services.source_capability_profile import get_capability_registry
from app.services.web_scraper_base import WebScraperSource, looks_javascript_rendered

# --- looks_javascript_rendered: pure heuristic, no browser needed ----------


def test_looks_javascript_rendered_detects_enable_javascript_shell() -> None:
    html = "<html><body>You need to enable JavaScript to run this app.</body></html>"
    assert looks_javascript_rendered(html) is True


def test_looks_javascript_rendered_detects_empty_body() -> None:
    html = '<html><body><div id="root"></div></body></html>'
    assert looks_javascript_rendered(html) is True


def test_looks_javascript_rendered_does_not_flag_thin_but_real_content() -> None:
    # Mirrors Colombia ICETEX's real reciprocity page (source #31) - real,
    # if thin, program content must never be misclassified as JS-only.
    html = (
        "<html><body><h1>Programa de reciprocidad para extranjeros en "
        "Colombia</h1><p>A través del programa de reciprocidad para "
        "extranjeros en Colombia, el ICETEX le brinda la oportunidad de "
        "venir a realizar estudios de especialización.</p></body></html>"
    )
    assert looks_javascript_rendered(html) is False


def test_looks_javascript_rendered_does_not_flag_normal_page() -> None:
    html = "<html><body>" + ("Real scholarship program content. " * 20) + "</body></html>"
    assert looks_javascript_rendered(html) is False


# --- WebScraperSource wiring: mocked, no browser needed ---------------------


class _FakeBrowserRenderingSource(WebScraperSource):
    source_code = "fake_browser_rendering_source"
    allow_browser_rendering = True
    browser_wait_for_selector = "#content"

    async def collect(self, **_: object) -> list:
        soup = await self.fetch_soup("https://example.test/scholarship")
        return [soup.get_text(strip=True)]


class _FakeHttpOnlySource(WebScraperSource):
    source_code = "fake_http_only_source"
    # allow_browser_rendering left at its False default deliberately.

    async def collect(self, **_: object) -> list:
        soup = await self.fetch_soup("https://example.test/scholarship")
        return [soup.get_text(strip=True)]


@pytest.mark.asyncio
async def test_thin_js_shell_falls_back_to_browser_rendering_when_opted_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_html(url: str, **_: object) -> str:
        return "<html><body>Loading...</body></html>"

    async def fake_fetch_rendered_html(url: str, **_: object) -> str:
        return "<html><body><div id='content'>Real rendered scholarship text</div></body></html>"

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)
    monkeypatch.setattr(
        browser_rendering, "fetch_rendered_html", fake_fetch_rendered_html
    )

    result = await _FakeBrowserRenderingSource().collect()

    assert result == ["Real rendered scholarship text"]


@pytest.mark.asyncio
async def test_fetch_html_records_requires_javascript_capability_for_any_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Capability evidence is recorded for every source's own domain
    regardless of whether it has opted into `allow_browser_rendering` -
    the point is to surface the "this looked like a JS shell" signal for
    a human to review, not to require opting in first just to observe it.
    """

    async def fake_get_html(url: str, **_: object) -> str:
        return "<html><body>Loading...</body></html>"

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)
    registry = get_capability_registry()
    registry.reset()

    await _FakeHttpOnlySource().collect()

    profile = registry.get("example.test")
    assert profile is not None
    assert profile.requires_javascript is True


@pytest.mark.asyncio
async def test_sources_that_never_opted_in_are_unaffected_by_a_thin_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_html(url: str, **_: object) -> str:
        return "<html><body>Loading...</body></html>"

    async def fail_if_called(url: str, **_: object) -> str:
        raise AssertionError(
            "browser rendering must never be attempted for a source that "
            "did not opt in"
        )

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)
    monkeypatch.setattr(browser_rendering, "fetch_rendered_html", fail_if_called)

    result = await _FakeHttpOnlySource().collect()

    assert result == ["Loading..."]


@pytest.mark.asyncio
async def test_browser_render_failure_falls_back_to_the_thin_http_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A browser-rendering failure (browser unavailable, navigation
    timeout, ...) must never crash the source's whole collect() call - it
    should fall back to the original (thin) HTTP response, matching how
    every other adapter degrades gracefully rather than raising.
    """

    async def fake_get_html(url: str, **_: object) -> str:
        return "<html><body>Loading...</body></html>"

    async def fake_fetch_rendered_html(url: str, **_: object) -> str:
        raise ExternalAPIError("Browser rendering is not available.")

    monkeypatch.setattr(web_scraper_base, "get_html", fake_get_html)
    monkeypatch.setattr(
        browser_rendering, "fetch_rendered_html", fake_fetch_rendered_html
    )

    result = await _FakeBrowserRenderingSource().collect()

    assert result == ["Loading..."]


# --- fetch_rendered_html: real headless-browser end-to-end tests -----------


def _chromium_available() -> bool:
    """Checks that a real browser can actually be launched, not just that
    the `playwright` package imports - `pip install playwright` alone
    does not install a browser binary (`playwright install chromium`
    does, separately), so import success alone would let these tests
    attempt a real launch and fail loudly instead of skipping cleanly.
    """
    try:
        import asyncio as _asyncio

        from playwright.async_api import async_playwright

        from app.core.config import get_settings

        async def _try_launch() -> bool:
            launch_kwargs: dict[str, object] = {"headless": True}
            if get_settings().browser_executable_path:
                launch_kwargs["executable_path"] = get_settings().browser_executable_path
            async with async_playwright() as p:
                browser = await p.chromium.launch(**launch_kwargs)
                await browser.close()
            return True

        return _asyncio.run(_try_launch())
    except Exception:  # noqa: BLE001 - any failure means "not available"
        return False


pytestmark_browser = pytest.mark.skipif(
    not _chromium_available(),
    reason="playwright/chromium is not installed in this environment",
)


class _TestHttpsServer:
    """A local, self-signed-HTTPS server on 127.0.0.1 for real
    browser-rendering tests - never leaves the machine, so it works the
    same in any sandboxed/offline test environment.
    """

    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self._status = status
        self.port = 0
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> str:
        body, status = self._body, self._status

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - stdlib method name
                self.send_response(status)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args: object) -> None:  # noqa: D102
                pass

        self._httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._httpd.server_address[1]

        cert_dir = Path(__file__).parent / ".tmp_test_certs"
        cert_dir.mkdir(exist_ok=True)
        cert_path, key_path = cert_dir / "cert.pem", cert_dir / "key.pem"
        if not cert_path.exists():
            subprocess.run(
                [
                    "openssl", "req", "-x509", "-newkey", "rsa:2048",
                    "-keyout", str(key_path), "-out", str(cert_path),
                    "-days", "1", "-nodes", "-subj", "/CN=127.0.0.1",
                ],
                check=True,
                capture_output=True,
            )

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(cert_path), str(key_path))
        self._httpd.socket = ctx.wrap_socket(self._httpd.socket, server_side=True)

        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return f"https://127.0.0.1:{self.port}"

    def __exit__(self, *_: object) -> None:
        assert self._httpd is not None
        self._httpd.shutdown()


@pytestmark_browser
@pytest.mark.asyncio
async def test_fetch_rendered_html_renders_real_javascript() -> None:
    """Proves the actual rendering mechanics - navigation, JS execution,
    rendered-DOM extraction - work end to end against a real headless
    Chromium. Launched directly (not through `fetch_rendered_html`, whose
    `validate_https_url` correctly has no opinion on certificate trust -
    that's the browser's job) against a local self-signed-HTTPS server,
    with `ignore_https_errors` scoped to this one test's own browser
    launch only; production code and every other test here go through
    the real, unmodified `fetch_rendered_html`.
    """
    html = (
        b"<html><body><div id='root'>Loading...</div>"
        b"<script>document.getElementById('root').innerHTML = "
        b"'<h1>Rendered Scholarship Title</h1>';</script></body></html>"
    )
    with _TestHttpsServer(html) as base_url:
        from playwright.async_api import async_playwright

        from app.core.config import get_settings

        launch_kwargs: dict[str, object] = {"headless": True}
        if get_settings().browser_executable_path:
            launch_kwargs["executable_path"] = get_settings().browser_executable_path

        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_kwargs)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            await page.goto(base_url, wait_until="networkidle", timeout=10_000)
            content = await page.content()
            root_div_text = await page.locator("#root").inner_text()
            await browser.close()

        assert root_div_text == "Rendered Scholarship Title"
        assert "Rendered Scholarship Title" in content


@pytestmark_browser
def test_challenge_page_detection_matches_known_signatures() -> None:
    assert browser_rendering._looks_like_a_challenge_page(
        "Attention Required! | Cloudflare", "Checking your browser before..."
    )
    assert browser_rendering._looks_like_a_challenge_page(
        "Just a moment...", "Please verify you are a human by completing the captcha."
    )
    assert not browser_rendering._looks_like_a_challenge_page(
        "Scholarship Program", "Real scholarship program details go here."
    )


# --- console/network-event classification: pure functions, no browser -----


def test_classify_console_text_flags_real_errors_as_error() -> None:
    assert (
        browser_rendering._classify_console_text(
            "Uncaught TypeError: cannot read property 'title' of undefined"
        )
        == "ERROR"
    )


def test_classify_console_text_downgrades_known_harmless_scripts_to_info() -> None:
    assert (
        browser_rendering._classify_console_text(
            "Failed to load resource: https://www.google-analytics.com/analytics.js"
        )
        == "INFO"
    )
    assert (
        browser_rendering._classify_console_text(
            "net::ERR_BLOCKED_BY_CLIENT loading doubleclick.net"
        )
        == "INFO"
    )


def test_classify_response_status_same_origin_5xx_is_critical() -> None:
    assert browser_rendering._classify_response_status(500, same_origin=True) == "CRITICAL"


def test_classify_response_status_third_party_5xx_is_warning() -> None:
    assert browser_rendering._classify_response_status(503, same_origin=False) == "WARNING"


def test_classify_response_status_same_origin_4xx_is_error() -> None:
    assert browser_rendering._classify_response_status(404, same_origin=True) == "ERROR"


def test_classify_response_status_third_party_4xx_is_info() -> None:
    assert browser_rendering._classify_response_status(404, same_origin=False) == "INFO"


# --- cookie/consent banner handling: real Chromium, no HTTPS-cert bypass ---
#
# `_maybe_accept_cookie_banner` is called directly (not through
# `render_page`/`fetch_rendered_html`) so these tests don't need to touch
# the production HTTPS-cert strictness `render_page` deliberately keeps -
# see `test_fetch_rendered_html_renders_real_javascript`'s docstring for
# the same reasoning.


@pytestmark_browser
@pytest.mark.asyncio
async def test_maybe_accept_cookie_banner_detects_and_clicks_real_banner() -> None:
    html = (
        b"<html><body>"
        b"<div id='cookie-banner'>"
        b"<p>We use cookies to improve your experience.</p>"
        b"<button onclick=\"document.getElementById('cookie-banner').style.display="
        b"'none'; document.getElementById('accepted-marker').textContent='yes';\">"
        b"Accept All Cookies</button>"
        b"</div>"
        b"<div id='content'>Scholarship content here</div>"
        b"<div id='accepted-marker'></div>"
        b"</body></html>"
    )
    with _TestHttpsServer(html) as base_url:
        from playwright.async_api import async_playwright

        from app.core.config import get_settings

        settings = get_settings()
        launch_kwargs: dict[str, object] = {"headless": True}
        if settings.browser_executable_path:
            launch_kwargs["executable_path"] = settings.browser_executable_path

        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_kwargs)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            await page.goto(base_url, wait_until="domcontentloaded", timeout=10_000)

            detected, handled = await browser_rendering._maybe_accept_cookie_banner(
                page, settings
            )
            marker_text = await page.locator("#accepted-marker").inner_text()
            await browser.close()

        assert detected is True
        assert handled is True
        assert marker_text == "yes"


@pytestmark_browser
@pytest.mark.asyncio
async def test_maybe_accept_cookie_banner_reports_not_detected_when_absent() -> None:
    html = b"<html><body><div id='content'>Scholarship content here</div></body></html>"
    with _TestHttpsServer(html) as base_url:
        from playwright.async_api import async_playwright

        from app.core.config import get_settings

        settings = get_settings()
        launch_kwargs: dict[str, object] = {"headless": True}
        if settings.browser_executable_path:
            launch_kwargs["executable_path"] = settings.browser_executable_path

        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_kwargs)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            await page.goto(base_url, wait_until="domcontentloaded", timeout=10_000)

            detected, handled = await browser_rendering._maybe_accept_cookie_banner(
                page, settings
            )
            await browser.close()

        assert detected is False
        assert handled is False


@pytestmark_browser
@pytest.mark.asyncio
async def test_maybe_accept_cookie_banner_does_not_click_when_disabled_by_config() -> None:
    html = (
        b"<html><body>"
        b"<div id='cookie-banner'><button>Accept</button></div>"
        b"<div id='content'>Scholarship content here</div>"
        b"</body></html>"
    )
    with _TestHttpsServer(html) as base_url:
        from playwright.async_api import async_playwright

        from app.core.config import Settings

        # `browser_auto_accept_required_cookies` carries a
        # `validation_alias` (AUTO_ACCEPT_REQUIRED_COOKIES), so pydantic
        # BaseSettings only binds a constructor kwarg by that alias name,
        # not the Python field name - matching how every other aliased
        # setting in this module is normally driven, via its env var.
        settings = Settings(AUTO_ACCEPT_REQUIRED_COOKIES=False)
        launch_kwargs: dict[str, object] = {"headless": True}
        if settings.browser_executable_path:
            launch_kwargs["executable_path"] = settings.browser_executable_path

        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_kwargs)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            await page.goto(base_url, wait_until="domcontentloaded", timeout=10_000)

            detected, handled = await browser_rendering._maybe_accept_cookie_banner(
                page, settings
            )
            await browser.close()

        assert detected is True
        assert handled is False


# --- render_page: full real-browser integration, monitoring + events ------


@pytestmark_browser
@pytest.mark.asyncio
async def test_render_page_captures_and_classifies_console_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Proves the `page.on("console", ...)` wiring inside `render_page`
    itself actually captures and classifies events (not just that the pure
    `_classify_console_text` helper works in isolation) - a real page-own
    error is reported as ERROR, a known-harmless third-party script error
    is downgraded to INFO, matching the spec's "don't fail a page over a
    harmless analytics error" requirement.

    Swaps the module's cached `_browser`/`_semaphore` for a real browser
    whose `new_context` transparently adds `ignore_https_errors=True`, so
    the full, real `render_page` function runs unmodified against the
    local self-signed-HTTPS test server - only the certificate-trust
    bypass (irrelevant to what's being tested here) is injected, exactly
    as `test_fetch_rendered_html_renders_real_javascript` does for a
    separately-launched browser.
    """
    html = (
        b"<html><head><title>Scholarship</title></head><body>"
        b"<div id='content'>Loaded</div>"
        b"<script>"
        b"console.error('Real app error: failed to load scholarships');"
        b"console.error('Failed to load resource: "
        b"https://www.google-analytics.com/analytics.js');"
        b"</script>"
        b"</body></html>"
    )
    with _TestHttpsServer(html) as base_url:
        from playwright.async_api import async_playwright

        from app.core.config import get_settings

        settings = get_settings()
        launch_kwargs: dict[str, object] = {"headless": True}
        if settings.browser_executable_path:
            launch_kwargs["executable_path"] = settings.browser_executable_path

        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_kwargs)
            real_new_context = browser.new_context

            async def _new_context_ignoring_https_errors(**kwargs: object):
                kwargs["ignore_https_errors"] = True
                return await real_new_context(**kwargs)

            monkeypatch.setattr(browser, "new_context", _new_context_ignoring_https_errors)
            monkeypatch.setattr(browser_rendering, "_browser", browser)
            monkeypatch.setattr(browser_rendering, "_semaphore", asyncio.Semaphore(2))

            result = await browser_rendering.render_page(
                base_url, wait_for_selector="#content", timeout_ms=10_000
            )

            await browser.close()

        real_errors = [e for e in result.events if e.severity == "ERROR"]
        harmless = [e for e in result.events if e.severity == "INFO"]
        assert any("Real app error" in e.message for e in real_errors)
        assert any("google-analytics" in e.message for e in harmless)
        assert all(e.type == "console_error" for e in real_errors + harmless)


@pytest.mark.asyncio
async def test_fetch_rendered_html_rejects_non_https_url() -> None:
    with pytest.raises(ExternalAPIError):
        await browser_rendering.fetch_rendered_html("http://example.test/insecure")


@pytest.mark.asyncio
async def test_fetch_rendered_html_raises_when_playwright_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_browser():
        raise browser_rendering.BrowserRenderingUnavailable(
            "Browser rendering is not available: the playwright package "
            "is not installed."
        )

    monkeypatch.setattr(browser_rendering, "_get_browser", fake_get_browser)

    with pytest.raises(browser_rendering.BrowserRenderingUnavailable):
        await browser_rendering.fetch_rendered_html("https://example.test/")
