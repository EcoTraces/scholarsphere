"""Tests for app/services/application_link_discovery.py. Real Chromium
against a local self-signed-HTTPS test server, same pattern as
tests/test_browser_interaction.py - skips cleanly when Playwright's
browser isn't installed.
"""

import asyncio
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from app.services import browser_rendering
from app.services.application_link_discovery import (
    _MAX_CLICK_CANDIDATES,
    discover_application_links,
)
from app.services.browser_interaction import BrowserInteractionEngine
from app.services.scraper_metrics import get_metrics


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
    except Exception:  # noqa: BLE001
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
            def do_GET(self) -> None:  # noqa: N802
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


@pytestmark_browser
@pytest.mark.asyncio
async def test_href_based_apply_link_is_discovered_without_clicking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = (
        b"<html><body>"
        b"<a href='/apply-form'>Apply Now</a>"
        b"</body></html>"
    )
    with _TestHttpsServer(html) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=5_000)
                candidates = await discover_application_links(engine, base_url=base_url)

        assert len(candidates) == 1
        assert candidates[0].discovery_method == "href"
        assert candidates[0].destination_url == base_url + "/apply-form"
        assert "Apply Now" in candidates[0].control_text


@pytestmark_browser
@pytest.mark.asyncio
async def test_click_reveals_new_tab_destination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = (
        b"<html><body>"
        b"<button onclick=\"window.open('/external-apply', '_blank')\">"
        b"Start Application</button>"
        b"</body></html>"
    )
    with _TestHttpsServer(html) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                # Longer timeout than the other tests in this file - a
                # real new OS-level browser tab (window.open) is slower
                # and more susceptible to flaking under system load
                # (parallel Chromium instances from other tests in the
                # same run) than an in-page DOM/URL change.
                engine = BrowserInteractionEngine(page, default_timeout_ms=15_000)
                candidates = await discover_application_links(engine, base_url=base_url)

        assert len(candidates) == 1
        assert candidates[0].discovery_method == "click_new_tab"
        assert candidates[0].destination_url is not None
        assert candidates[0].destination_url.endswith("/external-apply")


@pytestmark_browser
@pytest.mark.asyncio
async def test_click_reveals_client_side_route_destination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = (
        b"<html><body>"
        b"<button onclick=\"history.pushState({}, '', '/apply-step-2')\">"
        b"Submit Application</button>"
        b"</body></html>"
    )
    with _TestHttpsServer(html) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=5_000)
                candidates = await discover_application_links(engine, base_url=base_url)

        assert len(candidates) == 1
        assert candidates[0].discovery_method == "click_url_change"
        assert candidates[0].destination_url is not None
        assert candidates[0].destination_url.endswith("/apply-step-2")


@pytestmark_browser
@pytest.mark.asyncio
async def test_click_candidates_are_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    buttons = "".join(
        f"<button onclick=\"document.title='clicked-{i}'\">Apply Now {i}</button>"
        for i in range(_MAX_CLICK_CANDIDATES + 5)
    )
    html = f"<html><body>{buttons}</body></html>".encode()

    with _TestHttpsServer(html) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=2_000)
                candidates = await discover_application_links(engine, base_url=base_url)

        assert len(candidates) == _MAX_CLICK_CANDIDATES


@pytestmark_browser
@pytest.mark.asyncio
async def test_discovery_increments_dynamic_application_links_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics = get_metrics()
    metrics.reset()
    html = (
        b"<html><body>"
        b"<button onclick=\"history.pushState({}, '', '/apply-step-2')\">"
        b"Submit Application</button>"
        b"</body></html>"
    )
    with _TestHttpsServer(html) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=5_000)
                await discover_application_links(engine, base_url=base_url)

        assert metrics.snapshot()["dynamic_application_links"] == 1


@pytestmark_browser
@pytest.mark.asyncio
async def test_page_with_no_apply_controls_returns_no_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = b"<html><body><p>Nothing to see here.</p></body></html>"
    with _TestHttpsServer(html) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=5_000)
                candidates = await discover_application_links(engine, base_url=base_url)

        assert candidates == []
