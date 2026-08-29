"""Discovers scholarship "Apply" links that only become available after
JavaScript renders the page - built on top of
`app.services.browser_interaction.BrowserInteractionEngine`.

This module only ever reads: it identifies likely application controls on
an already-rendered page (matched against a broad set of apply-style
phrases, not just the literal word "Apply"), inspects `href` directly
where an `<a>` tag has one, and for controls without one (a `<button>`, or
a JS-driven `<a href="#">`), clicks through the engine and observes where
that leads - a new tab, a URL change (full navigation or a client-side
route), or an in-page DOM change (a modal) - via
`wait_for_navigation_or_change`. It never fills in a form, never enters
applicant information, never creates an account, and never submits
anything - see `app.services.browser_rendering`'s module docstring for
this project's standing policy, which applies identically here.

Every discovered candidate still has to pass
`app.services.application_link_validation.validate_application_link`
before it's treated as verified - this module only discovers candidates
and records how each was found; it never marks anything "valid" itself.

Bounded: at most `_MAX_CLICK_CANDIDATES` controls without a plain `href`
are ever clicked per page, so a page with many false-positive matches
can't turn into an unbounded click spree.
"""

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.services.browser_interaction import BrowserInteractionEngine
from app.services.scraper_metrics import get_metrics
from app.services.source_capability_profile import get_capability_registry
from app.services.web_scraper_base import absolute_https_url

logger = logging.getLogger(__name__)

#: Deliberately broader than the literal word "Apply" - matches every
#: example phrase from the spec ("Apply", "Apply Now", "Apply Online",
#: "Application", "Start Application", "Submit Application", "Scholarship
#: Application", "Official Application") without relying solely on exact
#: button text.
_APPLY_CONTROL_TEXT_PATTERN = re.compile(
    r"apply(\s+(now|online))?|"
    r"(start|submit|begin)\s+(your\s+)?application|"
    r"(scholarship|official|online)\s+application|"
    r"^application$",
    re.IGNORECASE,
)

#: Never click more than this many href-less candidate controls on one
#: page - a bound against a page with many false-positive text matches.
_MAX_CLICK_CANDIDATES = 5


@dataclass
class ApplicationLinkCandidate:
    control_text: str
    #: "href" (read directly, no click needed) | "click_new_tab" |
    #: "click_url_change" | "click_dom_change" | "click_no_change" (the
    #: click didn't observably lead anywhere within the timeout).
    discovery_method: str
    #: None only for "click_dom_change" (a modal opened in place, with no
    #: distinct URL of its own) and "click_no_change".
    destination_url: str | None


async def discover_application_links(
    engine: BrowserInteractionEngine, *, base_url: str
) -> list[ApplicationLinkCandidate]:
    """Scans the page `engine` is currently on for apply-style controls
    and returns one `ApplicationLinkCandidate` per match found (deduped
    by destination URL where one was determined). Leaves the page
    navigated back to `base_url` when a click-based candidate changed it,
    so a caller iterating multiple sources' listing pages always starts
    each page's discovery from that page's own content.
    """
    page = engine.page
    metrics = get_metrics()
    candidates: list[ApplicationLinkCandidate] = []
    seen_destinations: set[str] = set()

    locator = page.locator("a, button").filter(  # type: ignore[attr-defined]
        has_text=_APPLY_CONTROL_TEXT_PATTERN
    )
    count = await locator.count()
    clicked = 0

    for i in range(count):
        control = locator.nth(i)
        try:
            text = (await control.inner_text()).strip()
            tag_name = await control.evaluate("(el) => el.tagName.toLowerCase()")
        except Exception:  # noqa: BLE001 - element detached/gone; skip it
            continue

        href = await control.get_attribute("href") if tag_name == "a" else None
        if href and href.strip() not in ("", "#"):
            destination = absolute_https_url(base_url, href)
            if destination and destination not in seen_destinations:
                seen_destinations.add(destination)
                candidates.append(
                    ApplicationLinkCandidate(
                        control_text=text,
                        discovery_method="href",
                        destination_url=destination,
                    )
                )
            continue

        if clicked >= _MAX_CLICK_CANDIDATES:
            continue
        clicked += 1

        try:
            await engine.mark_baseline()
            await control.click(timeout=engine.default_timeout_ms)
        except Exception as exc:  # noqa: BLE001
            logger.info("application_link_click_failed text=%r error=%s", text, exc)
            continue

        outcome = await engine.wait_for_navigation_or_change()
        metrics.increment("dynamic_application_links")

        destination: str | None = None
        method = f"click_{outcome.kind}"
        if outcome.kind in ("new_tab", "url_change") and outcome.url:
            destination = outcome.url
            base_host = urlsplit(base_url).hostname
            if base_host:
                get_capability_registry().record(
                    base_host, dynamic_application_links=True
                )

        if destination and destination not in seen_destinations:
            seen_destinations.add(destination)
        candidates.append(
            ApplicationLinkCandidate(
                control_text=text, discovery_method=method, destination_url=destination
            )
        )

        if outcome.new_page is not None:
            try:
                await outcome.new_page.close()
            except Exception:  # noqa: BLE001
                pass
        if outcome.kind in ("url_change", "dom_change"):
            try:
                await page.goto(  # type: ignore[attr-defined]
                    base_url,
                    wait_until="domcontentloaded",
                    timeout=engine.default_timeout_ms,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "application_link_discovery_could_not_return_to_base "
                    "base_url=%s error=%s",
                    base_url,
                    exc,
                )

    return candidates
