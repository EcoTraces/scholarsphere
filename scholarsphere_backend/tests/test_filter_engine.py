"""Tests for app/services/filter_engine.py.

`iter_filter_combinations` is pure and tested without a browser.
`apply_filters` needs a live page to select/click against - real Chromium
against a local self-signed-HTTPS test server, same pattern as the other
real-browser test files; skips cleanly when Playwright's browser isn't
installed.
"""

import asyncio
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from app.services import browser_rendering
from app.services.browser_interaction import BrowserInteractionEngine
from app.services.filter_engine import FilterSpec, apply_filters, iter_filter_combinations
from app.services.source_capability_profile import get_capability_registry

# --- iter_filter_combinations: pure, no browser needed ---------------------


def test_iter_filter_combinations_is_a_bounded_cartesian_product() -> None:
    options = {
        "degree": [FilterSpec("#degree", "Master"), FilterSpec("#degree", "PhD")],
        "country": [FilterSpec("#country", "International")],
    }

    combos = list(iter_filter_combinations(options, max_combinations=10))

    assert len(combos) == 2
    assert {c["degree"].value for c in combos} == {"Master", "PhD"}
    assert all(c["country"].value == "International" for c in combos)


def test_iter_filter_combinations_respects_max_combinations() -> None:
    options = {
        "degree": [
            FilterSpec("#degree", "Bachelor"),
            FilterSpec("#degree", "Master"),
            FilterSpec("#degree", "PhD"),
        ],
        "field": [FilterSpec("#field", "Engineering"), FilterSpec("#field", "Medicine")],
    }

    combos = list(iter_filter_combinations(options, max_combinations=3))

    assert len(combos) == 3


def test_iter_filter_combinations_empty_options_yields_nothing() -> None:
    assert list(iter_filter_combinations({}, max_combinations=5)) == []


# --- apply_filters: real Chromium -------------------------------------------


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


_FILTER_PAGE_HTML = b"""
<html><body>
<select id="degree" onchange="document.getElementById('results').textContent='Filtered: ' + this.value;">
  <option value="">Any</option>
  <option value="Master">Master</option>
  <option value="PhD">PhD</option>
</select>
<div id="results">Unfiltered</div>
</body></html>
"""


@pytestmark_browser
@pytest.mark.asyncio
async def test_apply_filters_selects_a_dropdown_and_detects_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _TestHttpsServer(_FILTER_PAGE_HTML) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=5_000)
                result = await apply_filters(
                    engine, {"degree": FilterSpec("#degree", "Master")}
                )
                results_text = await page.locator("#results").inner_text()

        assert result.applied == {"degree": "Master"}
        assert result.skipped == []
        assert result.results_changed is True
        assert results_text == "Filtered: Master"


@pytestmark_browser
@pytest.mark.asyncio
async def test_apply_filters_skips_a_filter_the_page_does_not_have(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _TestHttpsServer(_FILTER_PAGE_HTML) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=5_000)
                result = await apply_filters(
                    engine,
                    {
                        "degree": FilterSpec("#degree", "Master"),
                        "country": FilterSpec("#country-not-present", "International"),
                    },
                )

        assert result.applied == {"degree": "Master"}
        assert result.skipped == ["country"]


@pytestmark_browser
@pytest.mark.asyncio
async def test_apply_filters_records_supports_filters_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_capability_registry().reset()
    with _TestHttpsServer(_FILTER_PAGE_HTML) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=5_000)
                await apply_filters(engine, {"degree": FilterSpec("#degree", "Master")})
                host = urlsplit(page.url).hostname

        profile = get_capability_registry().get(host)
        assert profile is not None
        assert profile.supports_filters is True
