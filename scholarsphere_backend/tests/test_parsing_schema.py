from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.parsing import (
    first_value,
    nested_value,
    parse_date,
    safe_float,
    safe_https_url,
    sanitize_html,
    utc_now,
)


def minimal_opportunity(**updates: object) -> dict[str, object]:
    values: dict[str, object] = {
        "source_code": "grants_gov",
        "external_id": "123",
        "title": "Education Grant",
        "opportunity_type": "grant",
        "provider_name": "Department of Education",
        "opportunity_status": "posted",
        "raw_payload": {"id": "123"},
    }
    values.update(updates)
    return values


def test_parsing_utilities_handle_external_values() -> None:
    assert str(parse_date("07/01/2026")) == "2026-07-01"
    assert parse_date("not-a-date") is None
    assert first_value(["first", "second"]) == "first"
    assert first_value([]) is None
    assert safe_float("$1,250.50") == 1250.5
    assert safe_float({"amount": "500"}) == 500
    assert safe_float("invalid") is None
    assert nested_value({"data": {"id": 7}}, "missing", "data.id") == 7
    assert safe_https_url("https://example.org/path") == "https://example.org/path"
    assert safe_https_url("http://example.org/path") is None


def test_html_sanitization_removes_active_content() -> None:
    result = sanitize_html(
        '<p>Hello <strong>world</strong></p>'
        '<script>alert("bad")</script>'
        '<a href="https://example.org">Source</a>'
    )

    assert result is not None
    assert "<script" not in result
    assert "alert" not in result
    assert "nofollow" in result


def test_utc_timestamp_is_timezone_aware() -> None:
    now = utc_now()
    assert now.tzinfo is UTC
    assert now.utcoffset() is not None


def test_normalized_schema_enforces_safe_defaults() -> None:
    opportunity = NormalizedExternalOpportunity(**minimal_opportunity())

    assert opportunity.verification_status == "pending"
    assert opportunity.publication_status == "unpublished"
    assert opportunity.collected_at.utcoffset() is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("verification_status", "verified"),
        ("publication_status", "published"),
        ("official_source_url", "http://example.org/opportunity"),
        ("collected_at", datetime(2026, 7, 1)),
    ],
)
def test_normalized_schema_rejects_unsafe_values(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        NormalizedExternalOpportunity(**minimal_opportunity(**{field: value}))
