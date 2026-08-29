"""Tests for app/services/source_capability_profile.py."""

from app.services.source_capability_profile import (
    SourceCapabilityClass,
    SourceCapabilityRegistry,
)


def test_record_creates_a_new_profile_on_first_observation() -> None:
    registry = SourceCapabilityRegistry()

    profile = registry.record("example.test", requires_javascript=True)

    assert profile.domain == "example.test"
    assert profile.requires_javascript is True
    assert profile.observation_count == 1
    assert profile.last_observed_at is not None


def test_record_merges_into_an_existing_profile_without_clobbering_unset_fields() -> None:
    registry = SourceCapabilityRegistry()

    registry.record("example.test", requires_javascript=True)
    profile = registry.record("example.test", cookie_banner=True)

    assert profile.requires_javascript is True
    assert profile.cookie_banner is True
    assert profile.observation_count == 2


def test_record_can_flip_a_previously_observed_value() -> None:
    registry = SourceCapabilityRegistry()

    registry.record("example.test", requires_javascript=True)
    profile = registry.record("example.test", requires_javascript=False)

    assert profile.requires_javascript is False


def test_get_returns_none_for_an_unobserved_domain() -> None:
    registry = SourceCapabilityRegistry()
    assert registry.get("never-seen.test") is None


def test_snapshot_and_reset() -> None:
    registry = SourceCapabilityRegistry()
    registry.record("a.test", requires_javascript=True)
    registry.record("b.test", requires_javascript=False)

    snapshot = registry.snapshot()
    assert set(snapshot) == {"a.test", "b.test"}

    registry.reset()
    assert registry.snapshot() == {}


def test_classification_blocked_takes_priority() -> None:
    registry = SourceCapabilityRegistry()
    profile = registry.record(
        "example.test", requires_javascript=True, public_api=True, blocked=True
    )
    assert profile.classification == SourceCapabilityClass.BLOCKED


def test_classification_public_api() -> None:
    registry = SourceCapabilityRegistry()
    profile = registry.record("example.test", public_api=True)
    assert profile.classification == SourceCapabilityClass.PUBLIC_API


def test_classification_spa_when_javascript_plus_rich_interaction() -> None:
    registry = SourceCapabilityRegistry()
    profile = registry.record(
        "example.test", requires_javascript=True, dynamic_application_links=True
    )
    assert profile.classification == SourceCapabilityClass.SPA


def test_classification_javascript_without_rich_interaction() -> None:
    registry = SourceCapabilityRegistry()
    profile = registry.record("example.test", requires_javascript=True)
    assert profile.classification == SourceCapabilityClass.JAVASCRIPT


def test_classification_static_html() -> None:
    registry = SourceCapabilityRegistry()
    profile = registry.record("example.test", requires_javascript=False)
    assert profile.classification == SourceCapabilityClass.STATIC_HTML


def test_classification_hybrid_static_with_cookie_banner() -> None:
    registry = SourceCapabilityRegistry()
    profile = registry.record(
        "example.test", requires_javascript=False, cookie_banner=True
    )
    assert profile.classification == SourceCapabilityClass.HYBRID


def test_classification_unknown_before_any_javascript_observation() -> None:
    registry = SourceCapabilityRegistry()
    profile = registry.record("example.test", cookie_banner=True)
    assert profile.classification is None
