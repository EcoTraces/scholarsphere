"""Validates a scholarship application URL - whether discovered statically
(an `<a href>` already present in a source's HTML) or dynamically (via
`app.services.application_link_discovery`, which finds links that only
appear after JavaScript renders an "Apply" control).

This module only ever reads: an HTTP GET (with redirects followed and
recorded) against the candidate URL, inspecting the final response's
status code, final URL/domain, and page title/text for application-page
keywords. It never submits a form, never creates an account, never enters
applicant information, and never attempts to log in - discovery and
verification only, matching this project's core policy (see
app/services/browser_rendering.py's module docstring for the same rule
applied to the browser-rendering layer).

Classification is intentionally conservative: only a link that resolves,
by domain, to either the source's own official domain or a domain a human
has pre-approved as an authorized external application portal
(`authorized_portal_domains`) can ever be marked VALID_*. Everything else -
including a perfectly reachable page on an unrecognized domain - comes
back UNKNOWN with `needs_review=True`. Per the spec this exists to satisfy:
"Never mark uncertain application links as verified."
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.http_client import validate_https_url
from app.services.scraper_metrics import get_metrics

logger = logging.getLogger(__name__)

#: Keywords (checked case-insensitively against the final page's title +
#: visible text) that indicate the page itself is an application flow, not
#: just an informational program description - deliberately not exhaustive;
#: absence just means "treated as informational", never "treated as
#: broken."
_APPLICATION_PAGE_MARKERS: tuple[str, ...] = (
    "apply now",
    "apply online",
    "start application",
    "submit application",
    "application form",
    "application portal",
    "create an account",
    "create account",
    "sign up",
    "register now",
    "begin your application",
)


class ApplicationLinkStatus(str, Enum):
    VALID_OFFICIAL_APPLICATION = "VALID_OFFICIAL_APPLICATION"
    VALID_AUTHORIZED_EXTERNAL_PORTAL = "VALID_AUTHORIZED_EXTERNAL_PORTAL"
    INFORMATION_PAGE_ONLY = "INFORMATION_PAGE_ONLY"
    BROKEN = "BROKEN"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


#: Only these two classifications represent an application link this
#: system has actually confirmed - everything else (including a reachable
#: but unrecognized-domain page) must not be treated as verified.
_VERIFIED_STATUSES = frozenset(
    {
        ApplicationLinkStatus.VALID_OFFICIAL_APPLICATION,
        ApplicationLinkStatus.VALID_AUTHORIZED_EXTERNAL_PORTAL,
    }
)


@dataclass
class ApplicationLinkValidation:
    original_url: str
    final_url: str | None
    status_code: int | None
    redirect_chain: list[str] = field(default_factory=list)
    classification: ApplicationLinkStatus = ApplicationLinkStatus.UNKNOWN
    reason: str = ""

    @property
    def needs_review(self) -> bool:
        return self.classification not in _VERIFIED_STATUSES


def _hostname(url: str) -> str | None:
    return urlsplit(url).hostname


def _same_domain(host: str | None, root: str | None) -> bool:
    if not host or not root:
        return False
    host, root = host.lower(), root.lower()
    return host == root or host.endswith(f".{root}")


def _matches_any_domain(host: str | None, roots: "list[str]") -> bool:
    return any(_same_domain(host, root) for root in roots)


def _looks_like_an_application_page(title: str, text: str) -> bool:
    haystack = f"{title}\n{text}".lower()
    return any(marker in haystack for marker in _APPLICATION_PAGE_MARKERS)


async def validate_application_link(
    url: str,
    *,
    source_domain: str | None = None,
    authorized_portal_domains: list[str] | None = None,
) -> ApplicationLinkValidation:
    """Fetches `url` (GET, redirects followed and recorded) and classifies
    it. Never raises for a bad/unreachable URL - every outcome, including
    "not even a valid HTTPS URL", comes back as a normal
    `ApplicationLinkValidation` result rather than an exception, since a
    broken discovered link is an expected, common outcome to record, not
    a bug in the caller.
    """
    result = await _validate_application_link(
        url,
        source_domain=source_domain,
        authorized_portal_domains=authorized_portal_domains,
    )
    metrics = get_metrics()
    if result.classification in _VERIFIED_STATUSES:
        metrics.increment("valid_application_links")
    elif result.classification == ApplicationLinkStatus.BROKEN:
        metrics.increment("broken_application_links")
    return result


async def _validate_application_link(
    url: str,
    *,
    source_domain: str | None = None,
    authorized_portal_domains: list[str] | None = None,
) -> ApplicationLinkValidation:
    try:
        validate_https_url(url)
    except Exception:
        return ApplicationLinkValidation(
            original_url=url,
            final_url=None,
            status_code=None,
            classification=ApplicationLinkStatus.BROKEN,
            reason="Not a valid HTTPS URL.",
        )

    settings = get_settings()
    authorized = authorized_portal_domains or []
    redirect_chain: list[str] = []

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.http_timeout_seconds),
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            async with client.stream(
                "GET",
                url,
                headers={
                    "User-Agent": (
                        "ScholarSphere/1.0 (+scholarship discovery; "
                        "opportunities@scholarsphere.app)"
                    ),
                },
            ) as response:
                redirect_chain = [str(r.url) for r in response.history]
                body = await response.aread()
                if len(body) > settings.http_max_response_bytes:
                    body = body[: settings.http_max_response_bytes]
                final_url = str(response.url)
                status_code = response.status_code
    except httpx.TooManyRedirects:
        return ApplicationLinkValidation(
            original_url=url,
            final_url=None,
            status_code=None,
            redirect_chain=redirect_chain,
            classification=ApplicationLinkStatus.BROKEN,
            reason="Too many redirects.",
        )
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
        return ApplicationLinkValidation(
            original_url=url,
            final_url=None,
            status_code=None,
            redirect_chain=redirect_chain,
            classification=ApplicationLinkStatus.BROKEN,
            reason=f"Connection failed: {type(exc).__name__}.",
        )

    if status_code in (401, 403):
        return ApplicationLinkValidation(
            original_url=url,
            final_url=final_url,
            status_code=status_code,
            redirect_chain=redirect_chain,
            classification=ApplicationLinkStatus.BLOCKED,
            reason="Access denied - authentication or authorization required.",
        )
    if status_code in (404, 410):
        return ApplicationLinkValidation(
            original_url=url,
            final_url=final_url,
            status_code=status_code,
            redirect_chain=redirect_chain,
            classification=ApplicationLinkStatus.BROKEN,
            reason="Page not found.",
        )
    if status_code >= 500:
        return ApplicationLinkValidation(
            original_url=url,
            final_url=final_url,
            status_code=status_code,
            redirect_chain=redirect_chain,
            classification=ApplicationLinkStatus.UNKNOWN,
            reason=f"Server error {status_code} - may be transient.",
        )
    if status_code >= 400:
        return ApplicationLinkValidation(
            original_url=url,
            final_url=final_url,
            status_code=status_code,
            redirect_chain=redirect_chain,
            classification=ApplicationLinkStatus.BROKEN,
            reason=f"Client error {status_code}.",
        )

    final_host = _hostname(final_url)
    soup = BeautifulSoup(body, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    text = soup.get_text(" ", strip=True)[:5000]

    if _same_domain(final_host, source_domain):
        if _looks_like_an_application_page(title, text):
            return ApplicationLinkValidation(
                original_url=url,
                final_url=final_url,
                status_code=status_code,
                redirect_chain=redirect_chain,
                classification=ApplicationLinkStatus.VALID_OFFICIAL_APPLICATION,
                reason="Reachable on the source's own domain with application-page content.",
            )
        return ApplicationLinkValidation(
            original_url=url,
            final_url=final_url,
            status_code=status_code,
            redirect_chain=redirect_chain,
            classification=ApplicationLinkStatus.INFORMATION_PAGE_ONLY,
            reason="Reachable on the source's own domain, but no application-page content found.",
        )

    if _matches_any_domain(final_host, authorized):
        return ApplicationLinkValidation(
            original_url=url,
            final_url=final_url,
            status_code=status_code,
            redirect_chain=redirect_chain,
            classification=ApplicationLinkStatus.VALID_AUTHORIZED_EXTERNAL_PORTAL,
            reason="Reachable on a pre-authorized external application-portal domain.",
        )

    return ApplicationLinkValidation(
        original_url=url,
        final_url=final_url,
        status_code=status_code,
        redirect_chain=redirect_chain,
        classification=ApplicationLinkStatus.UNKNOWN,
        reason=(
            "Reachable, but the destination domain is neither the source's "
            "own domain nor a pre-authorized application-portal domain - "
            "needs human review before being treated as verified."
        ),
    )
