import logging
from types import SimpleNamespace

import httpx
import pytest
import respx

from app.core import http_client
from app.core.http_client import ExternalAPIError, get_html, post_json

URL = "https://api.example.test/search"
PAGE_URL = "https://pages.example.test/scholarship"


def settings(*, retries: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        http_timeout_seconds=1,
        http_max_retries=retries,
        http_max_response_bytes=1024,
    )


@pytest.mark.asyncio
@respx.mock
async def test_post_json_sets_protected_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(http_client, "get_settings", lambda: settings())
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"ok": True}))

    result = await post_json(
        URL,
        json={"query": "education"},
        headers={
            "Authorization": "secret-value",
            "User-Agent": "Caller/1.0",
            "X-Correlation-ID": "caller-value",
        },
    )

    assert result == {"ok": True}
    request = route.calls[0].request
    assert request.headers["User-Agent"] == "ScholarSphere/1.0"
    assert request.headers["X-Correlation-ID"] != "caller-value"
    assert request.headers["Authorization"] == "secret-value"


@pytest.mark.asyncio
async def test_post_json_rejects_non_https() -> None:
    with pytest.raises(ExternalAPIError, match="HTTPS"):
        await post_json("http://api.example.test/search")


@pytest.mark.asyncio
@respx.mock
async def test_post_json_rejects_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(http_client, "get_settings", lambda: settings())
    respx.post(URL).mock(
        return_value=httpx.Response(
            200,
            text="not-json",
            headers={"Content-Type": "application/json"},
        )
    )

    with pytest.raises(ExternalAPIError, match="invalid JSON"):
        await post_json(URL)


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 401, 403, 404])
@respx.mock
async def test_permanent_errors_are_not_retried(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    monkeypatch.setattr(http_client, "get_settings", lambda: settings(retries=3))
    route = respx.post(URL).mock(return_value=httpx.Response(status_code))

    with pytest.raises(ExternalAPIError) as captured:
        await post_json(URL)

    assert captured.value.status_code == status_code
    assert route.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [429, 500])
@respx.mock
async def test_temporary_http_errors_are_retried(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    monkeypatch.setattr(http_client, "get_settings", lambda: settings(retries=1))

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(http_client.asyncio, "sleep", no_sleep)
    route = respx.post(URL).mock(
        side_effect=[
            httpx.Response(status_code),
            httpx.Response(200, json={"ok": True}),
        ]
    )

    assert await post_json(URL) == {"ok": True}
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_timeout_is_retried_and_returns_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(http_client, "get_settings", lambda: settings(retries=1))

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(http_client.asyncio, "sleep", no_sleep)
    route = respx.post(URL).mock(side_effect=httpx.ReadTimeout("secret timeout"))

    with pytest.raises(ExternalAPIError, match="temporarily unavailable"):
        await post_json(URL, headers={"X-API-Key": "never-log-this"})

    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_retry_log_does_not_contain_sensitive_headers(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(http_client, "get_settings", lambda: settings())
    respx.post(URL).mock(return_value=httpx.Response(500))

    with caplog.at_level(logging.WARNING), pytest.raises(ExternalAPIError):
        await post_json(URL, headers={"X-API-Key": "never-log-this"})

    assert "api.example.test" in caplog.text
    assert "never-log-this" not in caplog.text


@pytest.mark.asyncio
@respx.mock
async def test_get_html_returns_decoded_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(http_client, "get_settings", lambda: settings())
    respx.get(PAGE_URL).mock(
        return_value=httpx.Response(200, text="<html><body>Hello</body></html>")
    )

    result = await get_html(PAGE_URL)

    assert result == "<html><body>Hello</body></html>"


@pytest.mark.asyncio
async def test_get_html_rejects_non_https() -> None:
    with pytest.raises(ExternalAPIError, match="HTTPS"):
        await get_html("http://pages.example.test/scholarship")


@pytest.mark.asyncio
@respx.mock
async def test_get_html_enforces_response_size_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_client,
        "get_settings",
        lambda: SimpleNamespace(
            http_timeout_seconds=1, http_max_retries=0, http_max_response_bytes=10
        ),
    )
    respx.get(PAGE_URL).mock(return_value=httpx.Response(200, text="x" * 1000))

    with pytest.raises(ExternalAPIError, match="too large"):
        await get_html(PAGE_URL)


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [429, 503])
@respx.mock
async def test_get_html_retries_temporary_errors(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    monkeypatch.setattr(http_client, "get_settings", lambda: settings(retries=1))

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(http_client.asyncio, "sleep", no_sleep)
    route = respx.get(PAGE_URL).mock(
        side_effect=[httpx.Response(status_code), httpx.Response(200, text="ok")]
    )

    assert await get_html(PAGE_URL) == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_get_html_permanent_error_is_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(http_client, "get_settings", lambda: settings(retries=3))
    route = respx.get(PAGE_URL).mock(return_value=httpx.Response(404))

    with pytest.raises(ExternalAPIError) as captured:
        await get_html(PAGE_URL)

    assert captured.value.status_code == 404
    assert route.call_count == 1
