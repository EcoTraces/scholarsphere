"""Real-Chromium tests for app/services/pagination_engine.py's
`paginate_by_click` - needs a live Playwright page to click a "Next"
control against, unlike `paginate_by_url` (tested with a plain fake in
tests/test_pagination_engine.py). Skips cleanly when Playwright's browser
isn't installed, same pattern as the other real-browser test files.
"""

import asyncio
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable

import pytest

from app.services import browser_rendering
from app.services.browser_interaction import BrowserInteractionEngine
from app.services.pagination_engine import paginate_by_click


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


class _DynamicHttpsServer:
    """Like the other test files' `_TestHttpsServer`, but the response
    body depends on the request path/query string - needed to serve a
    different "page" of results per `?page=N`.
    """

    def __init__(self, route_fn: Callable[[str], bytes]) -> None:
        self._route_fn = route_fn
        self.port = 0
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> str:
        route_fn = self._route_fn

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                body = route_fn(self.path)
                self.send_response(200)
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


_PAGES = {
    "1": (["A", "B"], "/?page=2"),
    "2": (["C", "D"], "/?page=3"),
    "3": (["E"], None),
}


def _route(path: str) -> bytes:
    page = "1"
    if "page=" in path:
        page = path.split("page=", 1)[1]
    items, next_href = _PAGES.get(page, ([], None))
    items_html = "".join(f"<div class='item'>{name}</div>" for name in items)
    next_html = f"<a id='next' href='{next_href}'>Next</a>" if next_href else ""
    return f"<html><body><div id='items'>{items_html}</div>{next_html}</body></html>".encode()


@pytestmark_browser
@pytest.mark.asyncio
async def test_paginate_by_click_walks_standard_next_button_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _DynamicHttpsServer(_route) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=5_000)

                async def extract_items() -> list[str]:
                    return await page.locator(".item").all_inner_texts()

                result = await paginate_by_click(
                    engine,
                    extract_items=extract_items,
                    next_control_selector="#next",
                    key_fn=lambda item: item,
                    max_pages=10,
                    max_records=100,
                )

        assert result.items == ["A", "B", "C", "D", "E"]
        assert result.pages_visited == 3
        assert result.stopped_reason == "no_next_control"


@pytestmark_browser
@pytest.mark.asyncio
async def test_paginate_by_click_stops_at_max_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _DynamicHttpsServer(_route) as base_url:
        async with _RealBrowserSession(monkeypatch):
            async with browser_rendering.interactive_session(base_url) as page:
                engine = BrowserInteractionEngine(page, default_timeout_ms=5_000)

                async def extract_items() -> list[str]:
                    return await page.locator(".item").all_inner_texts()

                result = await paginate_by_click(
                    engine,
                    extract_items=extract_items,
                    next_control_selector="#next",
                    key_fn=lambda item: item,
                    max_pages=2,
                    max_records=100,
                )

        assert result.pages_visited == 2
        assert result.stopped_reason == "max_pages_reached"
        assert result.items == ["A", "B", "C", "D"]
