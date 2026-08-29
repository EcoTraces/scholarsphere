"""Tests for app/services/browser_interaction.py (BrowserInteractionEngine)
and app/services/browser_rendering.py's `interactive_session`.

Launches a real headless Chromium against a local self-signed-HTTPS test
server, same pattern as tests/test_browser_rendering.py - skips cleanly
(not fail) when Playwright's browser isn't installed in the current
environment. `interactive_session`'s own HTTPS-cert strictness is bypassed
the same way `test_render_page_captures_and_classifies_console_errors`
does it: the module's cached `_browser`/`_semaphore` are swapped for a
real browser whose `new_context` transparently adds
`ignore_https_errors=True`, so the real, unmodified `interactive_session`
and `BrowserInteractionEngine` run exactly as they would in production.
"""

import asyncio
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from app.services import browser_rendering
from app.services.browser_interaction import BrowserInteractionEngine


def _chromium_available() -> bool:
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


class _RealBrowserSession:
    """Launches a real Chromium and swaps it into browser_rendering's
    module-cached `_browser`/`_semaphore` for the duration of the `with`
    block, with `ignore_https_errors=True` injected into every new
    context - see this file's module docstring for why.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._monkeypatch = monkeypatch
        self._playwright = None
        self._browser = None

    async def __aenter__(self) -> None:
        from playwright.async_api import async_playwright

        from app.core.config import get_settings

        settings = get_settings()
        launch_kwargs: dict[str, object] = {"headless": True}
        if settings.browser_executable_path:
            launch_kwargs["executable_path"] = settings.browser_executable_path

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(**launch_kwargs)
        real_new_context = self._browser.new_context

        async def _patched(**kwargs: object):
            kwargs["ignore_https_errors"] = True
            return await real_new_context(**kwargs)

        self._monkeypatch.setattr(self._browser, "new_context", _patched)
        self._monkeypatch.setattr(browser_rendering, "_browser", self._browser)
        self._monkeypatch.setattr(browser_rendering, "_semaphore", asyncio.Semaphore(2))

    async def __aexit__(self, *_: object) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()


_DOM_CHANGE_HTML = (
    b"<html><body>"
    b"<div id='content'>Original</div>"
    b"<button id='reveal' onclick=\"document.getElementById('content')."
    b"innerHTML='Detail revealed';\">View details</button>"
    b"</body></html>"
)

_URL_CHANGE_HTML = (
    b"<html><body>"
    b"<div id='content'>Original</div>"
    b"<button id='go' onclick=\"history.pushState({}, '', '/detail');\">"
    b"Open route</button>"
    b"</body></html>"
)

_NEW_TAB_HTML = (
    b"<html><body>"
    b"<a id='ext' href='/other-page' target='_blank'>Open in new tab</a>"
    b"</body></html>"
)

_NO_CHANGE_HTML = (
    b"<html><body>"
    b"<button id='noop'>Does nothing</button>"
    b"</body></html>"
)


@pytestmark_browser
@pytest.mark.asyncio
async def test_click_and_wait_detects_dom_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _TestHttpsServer(_DOM_CHANGE_HTML) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=5_000)
                await engine.click("#reveal")
                outcome = await engine.wait_for_navigation_or_change()

        assert outcome.kind == "dom_change"


@pytestmark_browser
@pytest.mark.asyncio
async def test_click_and_wait_detects_client_side_route_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _TestHttpsServer(_URL_CHANGE_HTML) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=5_000)
                await engine.click("#go")
                outcome = await engine.wait_for_navigation_or_change()

        assert outcome.kind == "url_change"
        assert outcome.url is not None
        assert outcome.url.endswith("/detail")


@pytestmark_browser
@pytest.mark.asyncio
async def test_click_and_wait_detects_new_tab(monkeypatch: pytest.MonkeyPatch) -> None:
    with _TestHttpsServer(_NEW_TAB_HTML) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                # A longer timeout than the other tests here - opening an
                # actual new OS-level browser tab is slower and more
                # susceptible to flaking under system load (parallel
                # Chromium instances from other tests in the same run)
                # than an in-page DOM/URL change.
                engine = BrowserInteractionEngine(page, default_timeout_ms=15_000)
                await engine.click("link", by="role", text="Open in new tab")
                outcome = await engine.wait_for_navigation_or_change()

        assert outcome.kind == "new_tab"
        assert outcome.new_page is not None
        assert outcome.url is not None
        assert outcome.url.endswith("/other-page")


@pytestmark_browser
@pytest.mark.asyncio
async def test_click_and_wait_reports_no_change_within_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _TestHttpsServer(_NO_CHANGE_HTML) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=500)
                await engine.click("#noop")
                outcome = await engine.wait_for_navigation_or_change(timeout_ms=500)

        assert outcome.kind == "no_change"


@pytestmark_browser
@pytest.mark.asyncio
async def test_engine_read_only_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    with _TestHttpsServer(_DOM_CHANGE_HTML) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page)
                await engine.wait_for_selector("#content", timeout_ms=5_000)
                content = await engine.capture_rendered_content()
                url = engine.extract_current_url()

        assert "Original" in content
        assert url == base_url + "/"
