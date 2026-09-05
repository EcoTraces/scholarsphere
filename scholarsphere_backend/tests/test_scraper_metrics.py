"""Tests for app/services/scraper_metrics.py."""

import pytest

from app.services.scraper_metrics import ScraperMetrics, get_metrics


def test_increment_defaults_to_one_and_accumulates() -> None:
    metrics = ScraperMetrics()
    metrics.increment("http_attempts")
    metrics.increment("http_attempts")
    metrics.increment("http_attempts", by=3)

    assert metrics.snapshot()["http_attempts"] == 5


def test_increment_rejects_unknown_counter() -> None:
    metrics = ScraperMetrics()
    with pytest.raises(KeyError):
        metrics.increment("not_a_real_counter")


def test_set_rejects_unknown_counter() -> None:
    metrics = ScraperMetrics()
    with pytest.raises(KeyError):
        metrics.set("not_a_real_counter", 5)


def test_set_overwrites_value() -> None:
    metrics = ScraperMetrics()
    metrics.increment("total_sources", by=10)
    metrics.set("total_sources", 43)

    assert metrics.snapshot()["total_sources"] == 43


def test_reset_zeroes_every_counter() -> None:
    metrics = ScraperMetrics()
    metrics.increment("http_attempts", by=5)
    metrics.increment("browser_fallbacks", by=2)

    metrics.reset()

    snapshot = metrics.snapshot()
    assert snapshot["http_attempts"] == 0
    assert snapshot["browser_fallbacks"] == 0


def test_snapshot_returns_a_copy_not_live_state() -> None:
    metrics = ScraperMetrics()
    metrics.increment("http_attempts")
    snapshot = metrics.snapshot()

    metrics.increment("http_attempts")

    assert snapshot["http_attempts"] == 1
    assert metrics.snapshot()["http_attempts"] == 2


def test_ratio_is_none_when_denominator_is_zero() -> None:
    """An untouched counter must read as 'not measured', never a fabricated
    0.0 that would misleadingly imply a real, observed zero rate.
    """
    metrics = ScraperMetrics()
    snapshot = metrics.snapshot()

    assert snapshot["browser_fallback_rate"] is None
    assert snapshot["browser_success_rate"] is None
    assert snapshot["application_link_success_rate"] is None
    assert snapshot["verification_rate"] is None
    assert snapshot["duplicate_rate"] is None
    assert snapshot["error_rate"] is None


def test_ratios_computed_correctly() -> None:
    metrics = ScraperMetrics()
    metrics.increment("http_attempts", by=10)
    metrics.increment("browser_fallbacks", by=4)
    metrics.increment("browser_successes", by=3)
    metrics.increment("browser_failures", by=1)
    metrics.increment("dynamic_application_links", by=5)
    metrics.increment("valid_application_links", by=4)
    metrics.increment("candidates_discovered", by=20)
    metrics.increment("opportunities_verified", by=12)
    metrics.increment("duplicates_removed", by=3)

    snapshot = metrics.snapshot()

    assert snapshot["browser_fallback_rate"] == pytest.approx(4 / 10)
    assert snapshot["browser_success_rate"] == pytest.approx(3 / 4)
    assert snapshot["application_link_success_rate"] == pytest.approx(4 / 5)
    assert snapshot["verification_rate"] == pytest.approx(12 / 20)
    assert snapshot["duplicate_rate"] == pytest.approx(3 / 20)
    assert snapshot["error_rate"] == pytest.approx(round(1 / 14, 4))


def test_get_metrics_returns_the_same_shared_instance() -> None:
    assert get_metrics() is get_metrics()
