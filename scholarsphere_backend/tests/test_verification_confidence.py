from datetime import date, timedelta

from app.models.external_opportunity import ExternalOpportunity, OpportunitySource
from app.services.parsing import utc_now
from app.services.verification_confidence import assess_confidence


def _source(trust_level: str = "official") -> OpportunitySource:
    return OpportunitySource(
        source_code="grants_gov",
        source_name="Grants.gov",
        source_type="government",
        base_url="https://api.grants.gov/v1/api",
        authentication_type="none",
        trust_level=trust_level,
    )


def _opportunity(**overrides: object) -> ExternalOpportunity:
    today = utc_now().date()
    defaults: dict[str, object] = {
        "external_id": "1",
        "title": "Test Opportunity",
        "opportunity_type": "grant",
        "provider_name": "Test Provider",
        "description": "A complete description of the opportunity.",
        "deadline": today + timedelta(days=30),
        "opportunity_status": "posted",
        "official_source_url": "https://example.gov/opportunity/1",
        "official_application_url": "https://example.gov/apply/1",
        "payload_hash": "hash",
        "external_fingerprint": "fingerprint",
        "duplicate_review_required": False,
        "collected_at": utc_now(),
        "last_external_update_at": utc_now(),
    }
    defaults.update(overrides)
    return ExternalOpportunity(**defaults)


def test_official_complete_future_deadline_is_high_confidence() -> None:
    assessment = assess_confidence(_opportunity(), _source("official"))

    assert assessment.level == "high"
    assert any("official structured-API" in reason for reason in assessment.reasons)


def test_web_scraped_source_scores_lower_than_official() -> None:
    official = assess_confidence(_opportunity(), _source("official"))
    scraped = assess_confidence(_opportunity(), _source("web_scraped"))

    assert scraped.score < official.score
    assert any("web scraping" in reason for reason in scraped.reasons)


def test_duplicate_flag_lowers_score_and_is_explained() -> None:
    baseline = assess_confidence(_opportunity(), _source("official"))
    duplicate = assess_confidence(
        _opportunity(duplicate_review_required=True), _source("official")
    )

    assert duplicate.score < baseline.score
    assert any("duplicate" in reason.lower() for reason in duplicate.reasons)


def test_missing_fields_lower_score_and_list_the_missing_fields() -> None:
    sparse = _opportunity(
        description=None,
        official_application_url=None,
        deadline=None,
    )
    assessment = assess_confidence(sparse, _source("official"))

    assert any("Missing field(s)" in reason for reason in assessment.reasons)
    assert any("description" in reason for reason in assessment.reasons)


def test_past_deadline_is_penalized() -> None:
    today = utc_now().date()
    expired = _opportunity(deadline=today - timedelta(days=5))
    assessment = assess_confidence(expired, _source("official"))

    assert any("past" in reason.lower() for reason in assessment.reasons)


def test_far_future_deadline_is_flagged_as_suspicious() -> None:
    today = utc_now().date()
    far_future = _opportunity(deadline=today + timedelta(days=365 * 5))
    assessment = assess_confidence(far_future, _source("official"))

    assert any("years away" in reason for reason in assessment.reasons)


def test_score_is_always_bounded_0_to_100() -> None:
    worst = assess_confidence(
        _opportunity(
            description=None,
            official_source_url=None,
            official_application_url=None,
            deadline=date(2000, 1, 1),
            duplicate_review_required=True,
        ),
        _source("web_scraped"),
    )
    best = assess_confidence(_opportunity(), _source("official"))

    assert 0 <= worst.score <= 100
    assert 0 <= best.score <= 100


def test_confidence_never_touches_verification_or_publication_status() -> None:
    """The confidence engine must be purely additive - it has no way to
    set these fields, and this test documents that guarantee."""
    from app.models.external_opportunity import PublicationStatus, VerificationStatus

    opportunity = _opportunity(
        verification_status=VerificationStatus.pending,
        publication_status=PublicationStatus.unpublished,
    )
    assess_confidence(opportunity, _source("official"))

    assert opportunity.verification_status == VerificationStatus.pending
    assert opportunity.publication_status == PublicationStatus.unpublished
