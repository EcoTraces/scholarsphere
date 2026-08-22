"""Explainable, deterministic confidence scoring for the pending
verification queue.

This exists to help a Verification Officer triage a growing queue - it
never sets `verification_status`, never publishes anything, and does not
change the mandatory human-approval gate described in
docs/OPPORTUNITY_VERIFICATION_SYSTEM.md: every opportunity still requires
an officer's explicit `approved` decision (with the four-item checklist)
before it can be published, regardless of its confidence level. This is a
sort/priority hint surfaced on `GET /pending-verification`
(`sort=confidence`), nothing more.

Deliberately not an AI/ML score - every factor and its point value is
listed below, and every result carries the specific reasons that produced
it, matching the platform's stated rule that AI output (if any is ever
added) must never itself decide verification status and that any scoring
system must be auditable (docs/OPPORTUNITY_VERIFICATION_SYSTEM.md SS10).
"""

from dataclasses import dataclass, field
from datetime import timedelta

from app.models.external_opportunity import ExternalOpportunity, OpportunitySource
from app.services.parsing import utc_now

OFFICIAL_TRUST_LEVEL = "official"
WEB_SCRAPED_TRUST_LEVEL = "web_scraped"

_COMPLETENESS_FIELDS = (
    "description",
    "deadline",
    "official_source_url",
    "official_application_url",
)


@dataclass
class ConfidenceAssessment:
    level: str  # "high" | "medium" | "low"
    score: int  # 0-100, for a stable sort order only - not shown as a bare number
    reasons: list[str] = field(default_factory=list)


def assess_confidence(
    opportunity: ExternalOpportunity, source: OpportunitySource
) -> ConfidenceAssessment:
    score = 0
    reasons: list[str] = []

    if source.trust_level == OFFICIAL_TRUST_LEVEL:
        score += 40
        reasons.append(f"{source.source_name} is an official structured-API source.")
    elif source.trust_level == WEB_SCRAPED_TRUST_LEVEL:
        score += 15
        reasons.append(
            f"{source.source_name} is collected by web scraping, not an "
            "official API or feed - confirm the source page directly."
        )
    else:
        score += 5
        reasons.append(
            f"{source.source_name} has trust level '{source.trust_level}'."
        )

    if opportunity.duplicate_review_required:
        score -= 25
        reasons.append(
            "Flagged as a possible cross-source duplicate - resolve before approving."
        )

    missing = [
        field_name
        for field_name in _COMPLETENESS_FIELDS
        if not getattr(opportunity, field_name)
    ]
    if not missing:
        score += 20
        reasons.append(
            "All key fields are present (description, deadline, source URL, "
            "application URL)."
        )
    else:
        score -= 10 * len(missing)
        reasons.append("Missing field(s): " + ", ".join(missing) + ".")

    today = utc_now().date()
    if opportunity.deadline is not None:
        if opportunity.deadline < today:
            score -= 30
            reasons.append("Deadline is already in the past.")
        elif opportunity.deadline > today + timedelta(days=365 * 3):
            score -= 15
            reasons.append(
                "Deadline is more than 3 years away - confirm it is not a "
                "parsing error."
            )
        else:
            score += 10
            reasons.append("Deadline is a plausible future date.")

    if opportunity.official_source_url and str(
        opportunity.official_source_url
    ).startswith("https://"):
        score += 10
    if opportunity.official_application_url and str(
        opportunity.official_application_url
    ).startswith("https://"):
        score += 10

    score = max(0, min(100, score))
    if score >= 70:
        level = "high"
    elif score >= 40:
        level = "medium"
    else:
        level = "low"

    return ConfidenceAssessment(level=level, score=score, reasons=reasons)
