"""In-process capability memory for scraper sources: what has this
engine actually observed about how a given domain behaves, across scans?

Same in-memory-only design as `app.services.scraper_metrics` (see that
module's docstring for why - it resets on process restart, and isn't a
persisted time series).

This is observability, not automation. Nothing here silently changes what
a source does: `WebScraperSource.allow_browser_rendering` (see
app/services/web_scraper_base.py) stays a deliberate, human-reviewed
decision made only after the kind of live per-source testing documented
in docs/AUTHORITATIVE_SOURCES.md. Recording "this domain returned a JS
shell over plain HTTP the last three times" here is meant to surface that
evidence for a human to review and then explicitly promote (by opting
that source class into `allow_browser_rendering`) - not to have the
engine reconfigure its own fetch strategy unsupervised. The spec's own
example ("First scan: HTTP -> insufficient, Browser -> required. Save:
requires_javascript = true. Future scans: go directly to browser
fallback") describes the *evidence* this module accumulates; deciding to
act on it is still, deliberately, a human step in this codebase.

`app.services.web_scraper_base._fetch_html`, `app.services.
browser_rendering.render_page`/`interactive_session`, `app.services.
application_link_discovery.discover_application_links`, `app.services.
pagination_engine`, and `app.services.infinite_scroll_engine` all call
`record()` with whatever they directly observed; nothing else needs to
know this module exists.
"""

import threading
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from app.services.parsing import utc_now


class SourceCapabilityClass(str, Enum):
    STATIC_HTML = "static_html"
    JAVASCRIPT = "javascript"
    SPA = "spa"
    PUBLIC_API = "public_api"
    HYBRID = "hybrid"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class SourceCapabilityProfile:
    domain: str
    requires_javascript: bool | None = None
    #: "none" | "url" | "click" | "infinite_scroll" - only set once one of
    #: app.services.pagination_engine/infinite_scroll_engine has actually
    #: been used against this domain.
    pagination_type: str | None = None
    supports_filters: bool | None = None
    dynamic_application_links: bool | None = None
    cookie_banner: bool | None = None
    public_api: bool | None = None
    blocked: bool | None = None
    observation_count: int = 0
    last_observed_at: datetime | None = None

    @property
    def classification(self) -> SourceCapabilityClass | None:
        if self.blocked:
            return SourceCapabilityClass.BLOCKED
        if self.public_api:
            return SourceCapabilityClass.PUBLIC_API
        if self.requires_javascript is True:
            rich_interaction = bool(
                self.dynamic_application_links
                or self.supports_filters
                or self.pagination_type in ("click", "infinite_scroll")
            )
            return (
                SourceCapabilityClass.SPA
                if rich_interaction
                else SourceCapabilityClass.JAVASCRIPT
            )
        if self.requires_javascript is False:
            return SourceCapabilityClass.HYBRID if self.cookie_banner else (
                SourceCapabilityClass.STATIC_HTML
            )
        return None


class SourceCapabilityRegistry:
    """Thread-safe. One process-wide instance is normally obtained via
    `get_capability_registry()`; the class itself stays importable so
    tests can construct an isolated instance instead of mutating shared
    global state.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._profiles: dict[str, SourceCapabilityProfile] = {}

    def record(
        self,
        domain: str,
        *,
        requires_javascript: bool | None = None,
        pagination_type: str | None = None,
        supports_filters: bool | None = None,
        dynamic_application_links: bool | None = None,
        cookie_banner: bool | None = None,
        public_api: bool | None = None,
        blocked: bool | None = None,
    ) -> SourceCapabilityProfile:
        updates = {
            "requires_javascript": requires_javascript,
            "pagination_type": pagination_type,
            "supports_filters": supports_filters,
            "dynamic_application_links": dynamic_application_links,
            "cookie_banner": cookie_banner,
            "public_api": public_api,
            "blocked": blocked,
        }
        with self._lock:
            existing = self._profiles.get(domain, SourceCapabilityProfile(domain=domain))
            changes = {key: value for key, value in updates.items() if value is not None}
            updated = replace(
                existing,
                observation_count=existing.observation_count + 1,
                last_observed_at=utc_now(),
                **changes,
            )
            self._profiles[domain] = updated
            return updated

    def get(self, domain: str) -> SourceCapabilityProfile | None:
        with self._lock:
            return self._profiles.get(domain)

    def snapshot(self) -> dict[str, SourceCapabilityProfile]:
        with self._lock:
            return dict(self._profiles)

    def reset(self) -> None:
        with self._lock:
            self._profiles.clear()


_registry = SourceCapabilityRegistry()


def get_capability_registry() -> SourceCapabilityRegistry:
    return _registry
