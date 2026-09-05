"""Tests for app/services/application_link_validation.py - all HTTP
interaction is mocked at the transport layer via `respx` (matching this
project's existing convention - see tests/test_http_client.py), never a
real network call, so these run offline/in CI without a browser.
"""

import httpx
import pytest
import respx

from app.services.application_link_validation import (
    ApplicationLinkStatus,
    validate_application_link,
)
from app.services.scraper_metrics import get_metrics


@pytest.mark.asyncio
async def test_rejects_non_https_url_without_raising() -> None:
    result = await validate_application_link("http://example.test/apply")

    assert result.classification == ApplicationLinkStatus.BROKEN
    assert result.needs_review is True


@pytest.mark.asyncio
@respx.mock
async def test_official_domain_with_application_content_is_valid() -> None:
    respx.get("https://gov.example.test/scholarships/apply").mock(
        return_value=httpx.Response(
            200,
            html="<html><head><title>Apply Now</title></head>"
            "<body>Start Application below.</body></html>",
        )
    )

    result = await validate_application_link(
        "https://gov.example.test/scholarships/apply",
        source_domain="gov.example.test",
    )

    assert result.classification == ApplicationLinkStatus.VALID_OFFICIAL_APPLICATION
    assert result.needs_review is False
    assert result.status_code == 200


@pytest.mark.asyncio
@respx.mock
async def test_official_domain_without_application_content_is_information_only() -> None:
    respx.get("https://gov.example.test/scholarships/overview").mock(
        return_value=httpx.Response(
            200,
            html="<html><head><title>Program Overview</title></head>"
            "<body>Details about the scholarship program.</body></html>",
        )
    )

    result = await validate_application_link(
        "https://gov.example.test/scholarships/overview",
        source_domain="gov.example.test",
    )

    assert result.classification == ApplicationLinkStatus.INFORMATION_PAGE_ONLY
    assert result.needs_review is True


@pytest.mark.asyncio
@respx.mock
async def test_authorized_external_portal_domain_is_valid() -> None:
    respx.get("https://gov.example.test/scholarships/apply").mock(
        return_value=httpx.Response(
            302, headers={"Location": "https://portal.applyexternal.test/form"}
        )
    )
    respx.get("https://portal.applyexternal.test/form").mock(
        return_value=httpx.Response(200, html="<html><body>Portal</body></html>")
    )

    result = await validate_application_link(
        "https://gov.example.test/scholarships/apply",
        source_domain="gov.example.test",
        authorized_portal_domains=["portal.applyexternal.test"],
    )

    assert result.classification == ApplicationLinkStatus.VALID_AUTHORIZED_EXTERNAL_PORTAL
    assert result.needs_review is False
    assert result.final_url == "https://portal.applyexternal.test/form"
    assert result.redirect_chain == ["https://gov.example.test/scholarships/apply"]


@pytest.mark.asyncio
@respx.mock
async def test_unrecognized_domain_is_unknown_and_needs_review() -> None:
    respx.get("https://gov.example.test/scholarships/apply").mock(
        return_value=httpx.Response(
            302, headers={"Location": "https://random-third-party.test/apply"}
        )
    )
    respx.get("https://random-third-party.test/apply").mock(
        return_value=httpx.Response(200, html="<html><body>Apply here</body></html>")
    )

    result = await validate_application_link(
        "https://gov.example.test/scholarships/apply",
        source_domain="gov.example.test",
    )

    assert result.classification == ApplicationLinkStatus.UNKNOWN
    assert result.needs_review is True


@pytest.mark.asyncio
@respx.mock
async def test_404_is_broken() -> None:
    respx.get("https://gov.example.test/gone").mock(return_value=httpx.Response(404))

    result = await validate_application_link(
        "https://gov.example.test/gone", source_domain="gov.example.test"
    )

    assert result.classification == ApplicationLinkStatus.BROKEN
    assert result.needs_review is True


@pytest.mark.asyncio
@respx.mock
async def test_403_is_blocked() -> None:
    respx.get("https://gov.example.test/protected").mock(return_value=httpx.Response(403))

    result = await validate_application_link(
        "https://gov.example.test/protected", source_domain="gov.example.test"
    )

    assert result.classification == ApplicationLinkStatus.BLOCKED


@pytest.mark.asyncio
@respx.mock
async def test_server_error_is_unknown_not_broken() -> None:
    """A 5xx might be a transient outage rather than a permanently dead
    link - classified UNKNOWN (needs review), not BROKEN, so a source
    isn't wrongly written off after one bad moment.
    """
    respx.get("https://gov.example.test/flaky").mock(return_value=httpx.Response(503))

    result = await validate_application_link(
        "https://gov.example.test/flaky", source_domain="gov.example.test"
    )

    assert result.classification == ApplicationLinkStatus.UNKNOWN


@pytest.mark.asyncio
@respx.mock
async def test_connection_failure_is_broken() -> None:
    respx.get("https://unreachable.example.test/apply").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    result = await validate_application_link("https://unreachable.example.test/apply")

    assert result.classification == ApplicationLinkStatus.BROKEN


@pytest.mark.asyncio
@respx.mock
async def test_valid_and_broken_links_increment_metrics() -> None:
    metrics = get_metrics()
    metrics.reset()
    respx.get("https://gov.example.test/apply").mock(
        return_value=httpx.Response(
            200, html="<html><head><title>Apply Now</title></head><body/></html>"
        )
    )
    respx.get("https://gov.example.test/missing").mock(return_value=httpx.Response(404))

    await validate_application_link(
        "https://gov.example.test/apply", source_domain="gov.example.test"
    )
    await validate_application_link(
        "https://gov.example.test/missing", source_domain="gov.example.test"
    )

    snapshot = metrics.snapshot()
    assert snapshot["valid_application_links"] == 1
    assert snapshot["broken_application_links"] == 1
