import asyncio
import logging
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class ExternalAPIError(Exception):
    """A safe external-service failure without secret response details."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def validate_https_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ExternalAPIError("External API URL must be a valid HTTPS URL.")


async def post_json(
    url: str,
    *,
    json: dict[str, Any] | None = None,
    data: Mapping[str, Any] | None = None,
    files: Mapping[str, Any] | None = None,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    return await _request_json(
        "POST", url, json=json, data=data, files=files, params=params, headers=headers
    )


async def get_json(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    override_user_agent: bool = True,
) -> dict[str, Any]:
    """GET a JSON resource.

    ``override_user_agent=False`` lets a caller's own ``User-Agent`` survive
    unchanged - some official APIs (e.g. USAJOBS) require the header to be
    the caller's registered contact address as part of authentication, not
    a generic client identifier.
    """
    return await _request_json(
        "GET",
        url,
        params=params,
        headers=headers,
        override_user_agent=override_user_agent,
    )


async def get_html(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> str:
    """GET an HTML/text resource with the same HTTPS-only, timeout, retry,
    and response-size protections as get_json/post_json - used by the web
    scraper adapters (app/services/web_scraper_base.py), which fetch HTML
    pages rather than JSON API responses.
    """
    validate_https_url(url)
    settings = get_settings()
    correlation_id = str(uuid4())
    safe_headers = {
        **dict(headers or {}),
        "Accept": "text/html,application/xhtml+xml",
        "X-Correlation-ID": correlation_id,
        "User-Agent": "ScholarSphere/1.0 (+scholarship discovery; opportunities@scholarsphere.app)",
    }
    timeout = httpx.Timeout(settings.http_timeout_seconds)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        max_redirects=5,
    ) as client:
        for attempt in range(settings.http_max_retries + 1):
            try:
                async with client.stream(
                    "GET", url, params=params, headers=safe_headers
                ) as response:
                    body = await response.aread()
                    if len(body) > settings.http_max_response_bytes:
                        raise ExternalAPIError("External page response is too large.")
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        if attempt < settings.http_max_retries:
                            retry_after = response.headers.get("Retry-After")
                            delay = (
                                min(float(retry_after), 30.0)
                                if retry_after and retry_after.isdigit()
                                else min(2**attempt, 10)
                            )
                            await asyncio.sleep(delay)
                            continue
                        logger.warning(
                            "External page retry exhausted "
                            "correlation_id=%s host=%s status_code=%s",
                            correlation_id,
                            urlsplit(url).hostname,
                            response.status_code,
                        )
                        raise ExternalAPIError(
                            "External page is temporarily unavailable.",
                            status_code=response.status_code,
                        )
                    if response.is_error:
                        logger.info(
                            "External page rejected request "
                            "correlation_id=%s host=%s status_code=%s",
                            correlation_id,
                            urlsplit(url).hostname,
                            response.status_code,
                        )
                        raise ExternalAPIError(
                            "External page rejected the request.",
                            status_code=response.status_code,
                        )
                    return response.text
            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            ) as exc:
                if attempt >= settings.http_max_retries:
                    logger.warning(
                        "External page request failed correlation_id=%s host=%s",
                        correlation_id,
                        urlsplit(url).hostname,
                    )
                    raise ExternalAPIError(
                        "External page is temporarily unavailable."
                    ) from exc
                await asyncio.sleep(min(2**attempt, 10))

    raise ExternalAPIError("External page request failed.")


async def _request_json(
    method: str,
    url: str,
    *,
    json: dict[str, Any] | None = None,
    data: Mapping[str, Any] | None = None,
    files: Mapping[str, Any] | None = None,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    override_user_agent: bool = True,
) -> dict[str, Any]:
    validate_https_url(url)
    settings = get_settings()
    correlation_id = str(uuid4())
    safe_headers = {
        **dict(headers or {}),
        "Accept": "application/json",
        "X-Correlation-ID": correlation_id,
    }
    if override_user_agent or "User-Agent" not in safe_headers:
        safe_headers["User-Agent"] = "ScholarSphere/1.0"
    timeout = httpx.Timeout(settings.http_timeout_seconds)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        max_redirects=5,
    ) as client:
        for attempt in range(settings.http_max_retries + 1):
            try:
                async with client.stream(
                    method,
                    url,
                    json=json,
                    data=data,
                    files=files,
                    params=params,
                    headers=safe_headers,
                ) as response:
                    body = await response.aread()
                    if len(body) > settings.http_max_response_bytes:
                        raise ExternalAPIError("External API response is too large.")
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        if attempt < settings.http_max_retries:
                            retry_after = response.headers.get("Retry-After")
                            delay = (
                                min(float(retry_after), 30.0)
                                if retry_after and retry_after.isdigit()
                                else min(2**attempt, 10)
                            )
                            await asyncio.sleep(delay)
                            continue
                        logger.warning(
                            "External API retry exhausted "
                            "correlation_id=%s host=%s status_code=%s",
                            correlation_id,
                            urlsplit(url).hostname,
                            response.status_code,
                        )
                        raise ExternalAPIError(
                            "External API is temporarily unavailable.",
                            status_code=response.status_code,
                        )
                    if response.is_error:
                        logger.info(
                            "External API rejected request "
                            "correlation_id=%s host=%s status_code=%s",
                            correlation_id,
                            urlsplit(url).hostname,
                            response.status_code,
                        )
                        raise ExternalAPIError(
                            "External API rejected the request.",
                            status_code=response.status_code,
                        )
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise ExternalAPIError(
                            "External API returned invalid JSON."
                        ) from exc
                    if not isinstance(payload, dict):
                        raise ExternalAPIError(
                            "External API returned an unexpected JSON structure."
                        )
                    return payload
            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            ) as exc:
                if attempt >= settings.http_max_retries:
                    logger.warning(
                        "External API request failed correlation_id=%s host=%s",
                        correlation_id,
                        urlsplit(url).hostname,
                    )
                    raise ExternalAPIError(
                        "External API is temporarily unavailable."
                    ) from exc
                await asyncio.sleep(min(2**attempt, 10))

    raise ExternalAPIError("External API request failed.")
