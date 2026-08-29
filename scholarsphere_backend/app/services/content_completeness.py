"""Post-render content-completeness verification for a scraped scholarship
listing's extracted fields.

`app.services.web_scraper_base.looks_javascript_rendered` only answers "did
the HTTP response look like an unrendered JS shell" - a cheap, pre-parse
heuristic used to decide whether to fall back to browser rendering at all.
It says nothing about whether the fields a scraper adapter actually pulled
out of the (HTTP- or browser-rendered) page are enough to make a usable
listing. This module is that second, structural check.

It deliberately takes a plain `Mapping[str, object]` of extracted field
values - the same shape an adapter builds right before attempting to
construct a `NormalizedExternalOpportunity` (see app/schemas/
external_opportunity.py) - rather than that pydantic model itself.
`NormalizedExternalOpportunity` enforces `title`/`provider_name` as
non-empty at construction time, so a record missing them can never become
one; this check runs *before* that construction attempt, so an adapter can
tell "no title/provider found - not worth even trying to build a record
and skip this listing" apart from "title/provider fine, but thin on detail
- build the record but flag it for review."

Fields are grouped CRITICAL / IMPORTANT / OPTIONAL per the spec:
  CRITICAL:  title, provider_name
  IMPORTANT: official_application_url, deadline, description (this
             schema has no separate "eligibility"/"degree_level" fields -
             description is where that text lives for every source
             currently integrated)
  OPTIONAL:  funding_type, award_floor, award_ceiling, opening_date,
             country, currency

This never sets `NormalizedExternalOpportunity.verification_status` -
that field is fixed to "pending" by the schema itself (externally
collected records are always pending; see docs/
OPPORTUNITY_VERIFICATION_SYSTEM.md and the schema's own field validator).
`evaluate_completeness` instead returns a `CompletenessResult` alongside
the record for the review/import pipeline to consult - the score alone is
never sufficient for verification: `needs_review` is forced True whenever
any CRITICAL field is missing, regardless of the numeric score, per the
spec's own "Do not use the score alone for verification" rule.
"""

from dataclasses import dataclass, field
from typing import Mapping

#: Field-name tiers, matched against the keys of the mapping passed to
#: `evaluate_completeness` (the same keys an adapter would pass to
#: `NormalizedExternalOpportunity(**fields)`). Weights within a tier sum
#: to that tier's total share of the 100-point score.
_CRITICAL_FIELDS: tuple[str, ...] = ("title", "provider_name")
_IMPORTANT_FIELDS: tuple[str, ...] = (
    "official_application_url",
    "deadline",
    "description",
)
_OPTIONAL_FIELDS: tuple[str, ...] = (
    "funding_type",
    "award_floor",
    "award_ceiling",
    "opening_date",
    "country",
    "currency",
)

_CRITICAL_TOTAL_WEIGHT = 50
_IMPORTANT_TOTAL_WEIGHT = 35
_OPTIONAL_TOTAL_WEIGHT = 15


@dataclass
class CompletenessResult:
    score: int
    band: str
    missing_critical: list[str] = field(default_factory=list)
    missing_important: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    needs_review: bool = False


def _is_present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _band_for(score: int) -> str:
    if score >= 90:
        return "complete"
    if score >= 75:
        return "acceptable"
    if score >= 50:
        return "incomplete"
    return "insufficient"


def evaluate_completeness(fields: Mapping[str, object]) -> CompletenessResult:
    """Scores the extracted `fields` 0-100 and reports which critical/
    important/optional field names are missing or blank. `needs_review` is
    True whenever any CRITICAL field is missing - the band/score describe
    overall thoroughness, they don't replace that hard rule.
    """
    score = 0.0
    missing_critical: list[str] = []
    missing_important: list[str] = []
    missing_optional: list[str] = []

    critical_weight = _CRITICAL_TOTAL_WEIGHT / len(_CRITICAL_FIELDS)
    for name in _CRITICAL_FIELDS:
        if _is_present(fields.get(name)):
            score += critical_weight
        else:
            missing_critical.append(name)

    important_weight = _IMPORTANT_TOTAL_WEIGHT / len(_IMPORTANT_FIELDS)
    for name in _IMPORTANT_FIELDS:
        if _is_present(fields.get(name)):
            score += important_weight
        else:
            missing_important.append(name)

    optional_weight = _OPTIONAL_TOTAL_WEIGHT / len(_OPTIONAL_FIELDS)
    for name in _OPTIONAL_FIELDS:
        if _is_present(fields.get(name)):
            score += optional_weight
        else:
            missing_optional.append(name)

    rounded_score = round(score)
    return CompletenessResult(
        score=rounded_score,
        band=_band_for(rounded_score),
        missing_critical=missing_critical,
        missing_important=missing_important,
        missing_optional=missing_optional,
        needs_review=bool(missing_critical),
    )
