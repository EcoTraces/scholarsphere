from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.testimonial import (
    TestimonialDisplayMode,
    TestimonialOutcome,
    TestimonialReactionType,
    TestimonialStatus,
    TestimonialVerificationStatus,
)

#: A closed vocabulary rather than free text, so the public "Features
#: used" filter/badges (Phase 4) can't drift into one-off strings that
#: never match anything. Mirrors the platform's real feature surface.
KNOWN_FEATURES: tuple[str, ...] = (
    "opportunity_discovery",
    "eligibility_matching",
    "application_preparation",
    "cv_builder",
    "document_management",
    "deadline_tracking",
    "guidance_plans",
    "ai_application_assistant",
    "calendar_sync",
    "notifications",
)

#: Character caps on free-text story fields. Generous enough for a real
#: case study, but bounded so a single submission can't exhaust storage
#: or make the moderation queue unreadable.
_SHORT_TEXT_MAX = 4000
_NAME_MAX = 255


def display_name_for(
    full_name: str, display_mode: TestimonialDisplayMode
) -> str:
    """Compute the *shown* name from the stored real name - never stored
    separately, so changing `display_mode` later can't leak a name a
    previous read already cached under a different mode.
    """
    name = full_name.strip()
    if display_mode == TestimonialDisplayMode.anonymous or not name:
        return "Anonymous Applicant"
    if display_mode == TestimonialDisplayMode.full_name:
        return name
    parts = name.split()
    if len(parts) == 1:
        return parts[0]
    first, last = parts[0], parts[-1]
    return f"{first} {last[0]}." if last else first


class TestimonialOpportunityInput(BaseModel):
    opportunity_id: UUID | None = None
    opportunity_name: str = Field(min_length=1, max_length=500)
    opportunity_provider: str = Field(min_length=1, max_length=512)
    opportunity_type: str = Field(min_length=1, max_length=128)
    country: str | None = Field(default=None, max_length=255)
    degree_level: str | None = Field(default=None, max_length=128)
    field_of_study: str | None = Field(default=None, max_length=255)
    success_year: int | None = Field(default=None, ge=1990, le=2100)
    outcome: TestimonialOutcome


class TestimonialExperienceInput(BaseModel):
    challenge: str | None = Field(default=None, max_length=_SHORT_TEXT_MAX)
    discovery_story: str | None = Field(default=None, max_length=_SHORT_TEXT_MAX)
    preparation_story: str | None = Field(default=None, max_length=_SHORT_TEXT_MAX)
    scholarsphere_help: str | None = Field(default=None, max_length=_SHORT_TEXT_MAX)
    outcome_narrative: str | None = Field(default=None, max_length=_SHORT_TEXT_MAX)
    impact: str | None = Field(default=None, max_length=_SHORT_TEXT_MAX)
    advice: str | None = Field(default=None, max_length=_SHORT_TEXT_MAX)
    features_used: list[str] = Field(default_factory=list)

    @field_validator("features_used")
    @classmethod
    def _known_features_only(cls, value: list[str]) -> list[str]:
        unknown = [item for item in value if item not in KNOWN_FEATURES]
        if unknown:
            raise ValueError(f"Unknown feature(s): {unknown!r}")
        # De-duplicate while preserving order.
        return list(dict.fromkeys(value))


class TestimonialProfileInput(BaseModel):
    full_name: str = Field(min_length=1, max_length=_NAME_MAX)
    university: str | None = Field(default=None, max_length=255)
    program: str | None = Field(default=None, max_length=255)
    photo_storage_path: str | None = Field(default=None, max_length=1024)


class TestimonialPrivacyInput(BaseModel):
    display_mode: TestimonialDisplayMode = TestimonialDisplayMode.first_name_last_initial
    show_university: bool = True
    show_country: bool = True
    show_program: bool = True
    show_photo: bool = False


class TestimonialDraftRequest(BaseModel):
    """The full submission wizard's payload - every step's fields in one
    body. Steps 1-5 map directly onto the four input models above; step 6
    (review) is client-side only (a preview of this same data); step 7
    (consent) is `consent_confirmed`, only meaningful at submit time.
    """

    opportunity: TestimonialOpportunityInput
    experience: TestimonialExperienceInput = TestimonialExperienceInput()
    profile: TestimonialProfileInput
    privacy: TestimonialPrivacyInput = TestimonialPrivacyInput()
    evidence_storage_paths: list[str] = Field(default_factory=list, max_length=5)


class TestimonialSubmitRequest(BaseModel):
    consent_confirmed: bool


class TestimonialModerationDecisionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=_SHORT_TEXT_MAX)


class TestimonialVerifyRequest(BaseModel):
    verification_method: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(default=None, max_length=_SHORT_TEXT_MAX)


class TestimonialReactionRequest(BaseModel):
    reaction_type: TestimonialReactionType


class TestimonialInternalNotesRequest(BaseModel):
    """Staff-only working notes - never serialized to `TestimonialOwnRead`
    or any public/summary schema, only `TestimonialAdminRead` (Phase 33:
    "Never expose internal verification notes publicly").
    """

    notes: str = Field(default="", max_length=_SHORT_TEXT_MAX)


def _badges(status: TestimonialStatus, verification_status: TestimonialVerificationStatus, featured: bool) -> list[str]:
    badges: list[str] = []
    if featured and status == TestimonialStatus.approved:
        badges.append("featured")
    if verification_status == TestimonialVerificationStatus.verified:
        badges.append("verified")
    elif status == TestimonialStatus.approved:
        badges.append("community")
    else:
        badges.append("under_review")
    return badges


class TestimonialSummaryRead(BaseModel):
    """Card-shaped view for list/search/featured/related-stories surfaces.

    Never includes `full_name`, `evidence_storage_paths`,
    `internal_notes`, or `rejection_reason` - a summary read is
    reachable by any authenticated user, not just the owner or staff.
    """

    id: UUID
    slug: str
    display_name: str
    photo_storage_path: str | None
    country: str | None
    university: str | None
    program: str | None
    degree_level: str | None
    field_of_study: str | None
    opportunity_name: str
    opportunity_provider: str
    opportunity_type: str
    outcome: TestimonialOutcome
    success_year: int | None
    verification_status: TestimonialVerificationStatus
    featured: bool
    badges: list[str]
    excerpt: str
    features_used: list[str]
    helpful_count: int
    inspiring_count: int
    useful_count: int
    created_at: datetime

    @classmethod
    def from_model(cls, row: Any) -> "TestimonialSummaryRead":
        display_name = display_name_for(row.full_name, row.display_mode)
        excerpt_source = row.outcome_narrative or row.scholarsphere_help or row.impact or ""
        excerpt = excerpt_source.strip()
        if len(excerpt) > 220:
            excerpt = excerpt[:217].rstrip() + "..."
        return cls(
            id=row.id,
            slug=row.slug,
            display_name=display_name,
            photo_storage_path=row.photo_storage_path if row.show_photo else None,
            country=row.country if row.show_country else None,
            university=row.university if row.show_university else None,
            program=row.program if row.show_program else None,
            degree_level=row.degree_level,
            field_of_study=row.field_of_study,
            opportunity_name=row.opportunity_name,
            opportunity_provider=row.opportunity_provider,
            opportunity_type=row.opportunity_type,
            outcome=row.outcome,
            success_year=row.success_year,
            verification_status=row.verification_status,
            featured=row.featured,
            badges=_badges(row.status, row.verification_status, row.featured),
            excerpt=excerpt,
            features_used=list(row.features_used),
            helpful_count=row.helpful_count,
            inspiring_count=row.inspiring_count,
            useful_count=row.useful_count,
            created_at=row.created_at,
        )


class TestimonialDetailRead(BaseModel):
    """Full public story-page view. Same privacy exclusions as the
    summary above, plus the long-form narrative fields.
    """

    id: UUID
    slug: str
    display_name: str
    photo_storage_path: str | None
    country: str | None
    university: str | None
    program: str | None
    degree_level: str | None
    field_of_study: str | None
    opportunity_id: UUID | None
    opportunity_name: str
    opportunity_provider: str
    opportunity_type: str
    outcome: TestimonialOutcome
    success_year: int | None
    challenge: str | None
    discovery_story: str | None
    preparation_story: str | None
    scholarsphere_help: str | None
    outcome_narrative: str | None
    impact: str | None
    advice: str | None
    features_used: list[str]
    verification_status: TestimonialVerificationStatus
    featured: bool
    badges: list[str]
    helpful_count: int
    inspiring_count: int
    useful_count: int
    view_count: int
    created_at: datetime

    @classmethod
    def from_model(cls, row: Any) -> "TestimonialDetailRead":
        return cls(
            id=row.id,
            slug=row.slug,
            display_name=display_name_for(row.full_name, row.display_mode),
            photo_storage_path=row.photo_storage_path if row.show_photo else None,
            country=row.country if row.show_country else None,
            university=row.university if row.show_university else None,
            program=row.program if row.show_program else None,
            degree_level=row.degree_level,
            field_of_study=row.field_of_study,
            opportunity_id=row.opportunity_id,
            opportunity_name=row.opportunity_name,
            opportunity_provider=row.opportunity_provider,
            opportunity_type=row.opportunity_type,
            outcome=row.outcome,
            success_year=row.success_year,
            challenge=row.challenge,
            discovery_story=row.discovery_story,
            preparation_story=row.preparation_story,
            scholarsphere_help=row.scholarsphere_help,
            outcome_narrative=row.outcome_narrative,
            impact=row.impact,
            advice=row.advice,
            features_used=list(row.features_used),
            verification_status=row.verification_status,
            featured=row.featured,
            badges=_badges(row.status, row.verification_status, row.featured),
            helpful_count=row.helpful_count,
            inspiring_count=row.inspiring_count,
            useful_count=row.useful_count,
            view_count=row.view_count,
            created_at=row.created_at,
        )


class TestimonialOwnRead(BaseModel):
    """The owner's own view of their submission - unlike the public
    reads above, this always shows the real (unmasked) fields the owner
    themselves entered, plus editorial state, so they can see exactly
    what was submitted and why it might have been rejected.
    Deliberately still excludes `internal_notes` (staff-only).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    status: TestimonialStatus
    verification_status: TestimonialVerificationStatus
    featured: bool
    opportunity_id: UUID | None
    opportunity_name: str
    opportunity_provider: str
    opportunity_type: str
    country: str | None
    degree_level: str | None
    field_of_study: str | None
    success_year: int | None
    outcome: TestimonialOutcome
    challenge: str | None
    discovery_story: str | None
    preparation_story: str | None
    scholarsphere_help: str | None
    outcome_narrative: str | None
    impact: str | None
    advice: str | None
    features_used: list[str]
    full_name: str
    university: str | None
    program: str | None
    photo_storage_path: str | None
    display_mode: TestimonialDisplayMode
    show_university: bool
    show_country: bool
    show_program: bool
    show_photo: bool
    evidence_storage_paths: list[str]
    rejection_reason: str | None
    submitted_at: datetime | None
    approved_at: datetime | None
    verified_at: datetime | None
    withdrawn_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TestimonialAdminRead(TestimonialOwnRead):
    """Everything the owner sees, plus staff-only fields."""

    user_id: str
    internal_notes: str | None
    verified_by: str | None
    verification_method: str | None
    last_moderator_id: str | None
    rejected_at: datetime | None


class TestimonialModerationHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    previous_status: str
    new_status: str
    actor_id: str
    notes: str
    created_at: datetime


class TestimonialPage(BaseModel):
    items: list[TestimonialSummaryRead]
    total: int
    page: int
    page_size: int


class TestimonialAdminPage(BaseModel):
    items: list[TestimonialAdminRead]
    total: int
    page: int
    page_size: int


class TestimonialStatsRead(BaseModel):
    """Every count here is a real aggregate query against `testimonials`
    at request time - never a fabricated or cached-forever number (Phase
    3's "never fabricate numbers" requirement). A count of zero is
    represented as `None` by the service for a field the UI should hide
    rather than show as "0", per Phase 3's "gracefully hide the
    statistic rather than displaying fake numbers".
    """

    total_stories: int | None
    verified_stories: int | None
    countries_represented: int | None
    opportunity_types_represented: int | None
    fields_of_study_represented: int | None
