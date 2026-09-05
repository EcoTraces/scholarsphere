"""Real-Chromium tests for app/services/infinite_scroll_engine.py - needs
a live page to actually scroll. Skips cleanly when Playwright's browser
isn't installed, same pattern as the other real-browser test files.
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
from app.services.infinite_scroll_engine import scroll_and_extract
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


# Loads 2 items initially, then appends 2 more per scroll event for the
# first 3 scrolls, then stops appending (simulating "end of results") -
# a tall spacer keeps the page genuinely scrollable throughout so
# `scrollTo(0, document.body.scrollHeight)` always dispatches a real
# `scroll` event.
_INFINITE_SCROLL_HTML = b"""
<html><body>
<div id="items"><div class="item">seed-0</div><div class="item">seed-1</div></div>
<div style="height:3000px"></div>
<script>
let batch = 0;
window.addEventListener('scroll', () => {
  if (batch >= 3) return;
  batch++;
  const container = document.getElementById('items');
  for (let i = 0; i < 2; i++) {
    const d = document.createElement('div');
    d.className = 'item';
    d.textContent = 'gen-' + batch + '-' + i;
    container.appendChild(d);
  }
});
</script>
</body></html>
"""


@pytestmark_browser
@pytest.mark.asyncio
async def test_scroll_and_extract_collects_progressively_loaded_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _TestHttpsServer(_INFINITE_SCROLL_HTML) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=2_000)

                async def extract_items() -> list[str]:
                    return await page.locator(".item").all_inner_texts()

                result = await scroll_and_extract(
                    engine,
                    extract_items=extract_items,
                    key_fn=lambda item: item,
                    max_scroll_iterations=20,
                    max_records=1000,
                    stagnation_limit=2,
                    scroll_timeout_ms=1_500,
                )

        assert len(result.items) == 8  # seed(2) + 3 batches of 2
        assert "seed-0" in result.items
        assert "gen-3-1" in result.items
        assert result.stopped_reason == "no_new_records"


@pytestmark_browser
@pytest.mark.asyncio
async def test_scroll_and_extract_stops_at_max_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _TestHttpsServer(_INFINITE_SCROLL_HTML) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=2_000)

                async def extract_items() -> list[str]:
                    return await page.locator(".item").all_inner_texts()

                result = await scroll_and_extract(
                    engine,
                    extract_items=extract_items,
                    key_fn=lambda item: item,
                    max_scroll_iterations=20,
                    max_records=4,
                    stagnation_limit=2,
                    scroll_timeout_ms=1_500,
                )

        assert len(result.items) == 4
        assert result.stopped_reason == "max_records_reached"


@pytestmark_browser
@pytest.mark.asyncio
async def test_scroll_and_extract_increments_infinite_scroll_pages_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics = get_metrics()
    metrics.reset()
    with _TestHttpsServer(_INFINITE_SCROLL_HTML) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=2_000)

                async def extract_items() -> list[str]:
                    return await page.locator(".item").all_inner_texts()

                await scroll_and_extract(
                    engine,
                    extract_items=extract_items,
                    key_fn=lambda item: item,
                    max_scroll_iterations=20,
                    max_records=1000,
                    stagnation_limit=2,
                    scroll_timeout_ms=1_500,
                )

        assert metrics.snapshot()["infinite_scroll_pages"] > 0
