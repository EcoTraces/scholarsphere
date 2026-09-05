"""Tests for app/services/content_completeness.py."""

from app.services.content_completeness import evaluate_completeness


def test_fully_populated_fields_score_complete() -> None:
    fields = {
        "title": "Fully Funded Master's Scholarship",
        "provider_name": "Ministry of Education",
        "description": "Covers tuition, travel, and a monthly stipend for eligible applicants.",
        "deadline": "2027-01-01",
        "official_application_url": "https://example.test/apply",
        "funding_type": "grant",
        "award_floor": 1000.0,
        "award_ceiling": 5000.0,
        "opening_date": "2026-01-01",
        "country": "Kenya",
        "currency": "USD",
    }

    result = evaluate_completeness(fields)

    assert result.score == 100
    assert result.band == "complete"
    assert result.missing_critical == []
    assert result.needs_review is False


def test_missing_provider_forces_needs_review_regardless_of_other_fields() -> None:
    fields = {
        "title": "Fully Funded Master's Scholarship",
        # provider_name omitted entirely
        "description": "Covers tuition, travel, and a monthly stipend for eligible applicants.",
        "deadline": "2027-01-01",
        "official_application_url": "https://example.test/apply",
        "funding_type": "grant",
        "award_floor": 1000.0,
        "award_ceiling": 5000.0,
        "opening_date": "2026-01-01",
        "country": "Kenya",
        "currency": "USD",
    }

    result = evaluate_completeness(fields)

    assert result.missing_critical == ["provider_name"]
    assert result.needs_review is True
    # A high score from every other field being present still doesn't
    # override the critical-field rule.
    assert result.score >= 50


def test_blank_string_field_counts_as_missing() -> None:
    fields = {"title": "A Scholarship", "provider_name": "   "}

    result = evaluate_completeness(fields)

    assert "provider_name" in result.missing_critical
    assert result.needs_review is True


def test_only_critical_fields_present_scores_exactly_fifty_and_incomplete() -> None:
    fields = {"title": "A Scholarship", "provider_name": "A Ministry"}

    result = evaluate_completeness(fields)

    assert result.score == 50
    assert result.band == "incomplete"
    assert result.needs_review is False
    assert set(result.missing_important) == {
        "official_application_url",
        "deadline",
        "description",
    }
    assert len(result.missing_optional) == 6


def test_no_fields_at_all_scores_insufficient() -> None:
    result = evaluate_completeness({})

    assert result.score == 0
    assert result.band == "insufficient"
    assert result.needs_review is True
    assert result.missing_critical == ["title", "provider_name"]


def test_important_fields_missing_but_critical_present_is_not_needs_review() -> None:
    fields = {
        "title": "A Scholarship",
        "provider_name": "A Ministry",
        "description": "Real description text about eligibility and funding.",
    }

    result = evaluate_completeness(fields)

    assert result.needs_review is False
    assert "description" not in result.missing_important
    assert "deadline" in result.missing_important


def test_band_thresholds_acceptable() -> None:
    # critical (50) + important (35) = 85
    fields = {
        "title": "A Scholarship",
        "provider_name": "A Ministry",
        "description": "Real description text about eligibility and funding.",
        "deadline": "2027-01-01",
        "official_application_url": "https://example.test/apply",
    }

    result = evaluate_completeness(fields)

    assert result.band == "acceptable"
    assert 75 <= result.score <= 89
