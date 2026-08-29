"""In-process counters for the hybrid HTTP/browser-rendering scholarship
discovery pipeline (app/services/web_scraper_base.py,
app/services/browser_rendering.py, app/services/application_link_discovery.py,
app/services/application_link_validation.py, app/services/
content_completeness.py). A single process-wide `ScraperMetrics` instance
(`get_metrics()`) is incremented in place by those modules as sources run,
and can be read back via `GET /api/v1/admin/scraper/metrics`
(app/api/v1/routes/admin_scraper_metrics.py).

Deliberately in-memory only, not persisted to the database or a time-series
store - this mirrors the project's existing "no heavyweight monitoring
platform unless the architecture actually requires one" preference (see
docs/AUTHORITATIVE_SOURCES.md's browser-rendering section), and resets on
every process restart (a Celery worker restart, a new API deployment). A
snapshot is a point-in-time view of counters accumulated since that
process started, not a durable historical record - if longer retention is
ever needed, the fix is scraping this endpoint into a real metrics
backend (Prometheus, CloudWatch, ...), not building one here.
"""

import threading
from typing import Final

#: Every counter this module tracks. Keeping this as the single source of
#: truth means `increment`/`set` reject a typo'd counter name immediately
#: (a silently-never-incremented counter is a much harder bug to notice).
_COUNTER_NAMES: Final[tuple[str, ...]] = (
    "total_sources",
    "sources_scanned",
    "http_attempts",
    "http_successes",
    "browser_fallbacks",
    "browser_successes",
    "browser_failures",
    "javascript_pages",
    "static_pages",
    "spa_pages",
    "pagination_pages",
    "infinite_scroll_pages",
    "dynamic_application_links",
    "valid_application_links",
    "broken_application_links",
    "cookie_banners_detected",
    "cookie_banners_handled",
    "console_errors",
    "network_failures",
    "captcha_blocks",
    "timeouts",
    "candidates_discovered",
    "opportunities_verified",
    "opportunities_rejected",
    "opportunities_needing_review",
    "duplicates_removed",
)


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    """Returns `None` (never a fabricated 0.0) when there's no denominator
    to compute a real ratio from - an untouched counter must read as "not
    measured yet", not as a real, observed zero rate.
    """
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


class ScraperMetrics:
    """Thread-safe counter bag. One process-wide instance is normally
    obtained via `get_metrics()`; the class itself stays importable so
    tests can construct an isolated instance instead of mutating shared
    global state.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {name: 0 for name in _COUNTER_NAMES}

    def increment(self, name: str, by: int = 1) -> None:
        if name not in self._counters:
            raise KeyError(f"Unknown scraper metric: {name!r}")
        with self._lock:
            self._counters[name] += by

    def set(self, name: str, value: int) -> None:
        if name not in self._counters:
            raise KeyError(f"Unknown scraper metric: {name!r}")
        with self._lock:
            self._counters[name] = value

    def reset(self) -> None:
        with self._lock:
            for name in self._counters:
                self._counters[name] = 0

    def snapshot(self) -> dict[str, int | float | None]:
        """A point-in-time copy of every counter plus derived ratios.
        Never returns a live reference to internal state.
        """
        with self._lock:
            counters: dict[str, int | float | None] = dict(self._counters)

        counters["browser_fallback_rate"] = _safe_ratio(
            counters["browser_fallbacks"], counters["http_attempts"]
        )
        counters["browser_success_rate"] = _safe_ratio(
            counters["browser_successes"], counters["browser_fallbacks"]
        )
        counters["application_link_success_rate"] = _safe_ratio(
            counters["valid_application_links"], counters["dynamic_application_links"]
        )
        counters["verification_rate"] = _safe_ratio(
            counters["opportunities_verified"], counters["candidates_discovered"]
        )
        counters["duplicate_rate"] = _safe_ratio(
            counters["duplicates_removed"], counters["candidates_discovered"]
        )
        error_denominator = counters["http_attempts"] + counters["browser_fallbacks"]
        error_numerator = (
            counters["browser_failures"]
            + counters["network_failures"]
            + counters["timeouts"]
        )
        counters["error_rate"] = _safe_ratio(error_numerator, error_denominator)
        return counters


_metrics = ScraperMetrics()


def get_metrics() -> ScraperMetrics:
    return _metrics
