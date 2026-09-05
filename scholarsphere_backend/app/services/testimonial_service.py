"""Business logic for the Success Stories / testimonials feature.

Kept as a dedicated service (rather than folding logic into the route
module) because the same operations - status transitions, privacy-aware
serialization, reaction counters - are exercised from three different
route surfaces (public, own, admin) and need to behave identically from
all three.
"""

from __future__ import annotations

import re
import secrets
from uuid import UUID

import bleach
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.testimonial import (
    PUBLIC_STATUSES,
    Testimonial,
    TestimonialModerationHistory,
    TestimonialReaction,
    TestimonialReactionType,
    TestimonialStatus,
    TestimonialVerificationStatus,
)
from app.schemas.testimonial import TestimonialDraftRequest
from app.services.parsing import utc_now

_SLUG_UNSAFE = re.compile(r"[^a-z0-9]+")
_URL_PATTERN = re.compile(r"https?://\S+")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
#: A deliberately small, conservative blocklist - this is an advisory
#: signal for a human moderator (Phase 32 forbids auto-rejecting
#: legitimate criticism), not a hard filter. Real moderation still reads
#: every submission.
_BLOCKED_TERMS = frozenset({"viagra", "casino", "crypto giveaway", "click here to win"})

#: Free-text fields sanitized (HTML stripped) before storage. Applies to
#: every long-form field a user can type into, closing the same class of
#: stored-XSS risk `sanitize_html` closes for scraped content.
_TEXT_FIELDS = (
    "challenge",
    "discovery_story",
    "preparation_story",
    "scholarsphere_help",
    "outcome_narrative",
    "impact",
    "advice",
)


class TestimonialError(Exception):
    """Raised for a business-rule violation; routes translate this to
    an appropriate HTTP status rather than letting it surface as a 500.
    """


def _strip_html(value: str | None) -> str | None:
    if value is None:
        return None
    return bleach.clean(value, tags=[], attributes={}, strip=True).strip() or None


def _slugify(text: str) -> str:
    base = _SLUG_UNSAFE.sub("-", text.lower()).strip("-")
    return base[:80] or "success-story"


async def _unique_slug(session: AsyncSession, seed: str) -> str:
    base = _slugify(seed)
    for _ in range(10):
        candidate = f"{base}-{secrets.token_hex(3)}"
        existing = await session.scalar(select(Testimonial.id).where(Testimonial.slug == candidate))
        if existing is None:
            return candidate
    # Astronomically unlikely to be reached, but never loop forever.
    return f"{base}-{secrets.token_hex(8)}"


def flag_reasons(payload: TestimonialDraftRequest) -> list[str]:
    """Advisory content-moderation flags surfaced to the reviewing admin
    (Phase 32/33) - never used to auto-reject, only to help a human
    moderator triage faster.
    """
    flags: list[str] = []
    combined = " ".join(
        filter(
            None,
            [
                payload.experience.challenge,
                payload.experience.discovery_story,
                payload.experience.preparation_story,
                payload.experience.scholarsphere_help,
                payload.experience.outcome_narrative,
                payload.experience.impact,
                payload.experience.advice,
            ],
        )
    ).lower()
    url_count = len(_URL_PATTERN.findall(combined))
    if url_count >= 2:
        flags.append(f"Contains {url_count} links - review before publishing.")
    if _EMAIL_PATTERN.search(combined):
        flags.append("Contains what looks like an email address.")
    hit_terms = [term for term in _BLOCKED_TERMS if term in combined]
    if hit_terms:
        flags.append(f"Matched blocked-term list: {', '.join(sorted(hit_terms))}.")
    return flags


def _apply_draft_fields(row: Testimonial, payload: TestimonialDraftRequest) -> None:
    opportunity = payload.opportunity
    experience = payload.experience
    profile = payload.profile
    privacy = payload.privacy

    row.opportunity_id = opportunity.opportunity_id
    row.opportunity_name = opportunity.opportunity_name
    row.opportunity_provider = opportunity.opportunity_provider
    row.opportunity_type = opportunity.opportunity_type
    row.country = opportunity.country
    row.degree_level = opportunity.degree_level
    row.field_of_study = opportunity.field_of_study
    row.success_year = opportunity.success_year
    row.outcome = opportunity.outcome

    for field in _TEXT_FIELDS:
        setattr(row, field, _strip_html(getattr(experience, field)))
    row.features_used = list(experience.features_used)

    row.full_name = _strip_html(profile.full_name) or profile.full_name.strip()
    row.university = profile.university
    row.program = profile.program
    row.photo_storage_path = profile.photo_storage_path

    row.display_mode = privacy.display_mode
    row.show_university = privacy.show_university
    row.show_country = privacy.show_country
    row.show_program = privacy.show_program
    row.show_photo = privacy.show_photo

    row.evidence_storage_paths = list(payload.evidence_storage_paths)


async def save_draft(
    session: AsyncSession,
    *,
    user_id: str,
    testimonial_id: UUID | None,
    payload: TestimonialDraftRequest,
) -> Testimonial:
    """Create a new draft, or update an existing one the caller owns.

    Editing is only allowed while the story is not actively in a staff
    queue or already public untouched - `draft` and `changes_requested`
    are editable; editing a `submitted`/`under_review`/`approved` story
    would let an applicant silently rewrite content a moderator already
    reviewed (or the public already read), so those are rejected here
    rather than in the route, so every caller gets the same rule.
    """
    if testimonial_id is None:
        row = Testimonial(
            user_id=user_id,
            slug=await _unique_slug(session, payload.opportunity.opportunity_name),
            opportunity_name="",
            opportunity_provider="",
            opportunity_type="",
            outcome=payload.opportunity.outcome,
            full_name="",
            status=TestimonialStatus.draft,
        )
        session.add(row)
    else:
        row = await session.get(Testimonial, testimonial_id)
        if row is None or row.user_id != user_id:
            raise TestimonialError("not_found")
        if row.status not in (TestimonialStatus.draft, TestimonialStatus.changes_requested):
            raise TestimonialError("not_editable")

    _apply_draft_fields(row, payload)
    if row.status == TestimonialStatus.changes_requested:
        row.status = TestimonialStatus.draft
    await session.flush()
    await session.refresh(row)
    return row


_REQUIRED_FOR_SUBMISSION: tuple[str, ...] = (
    "opportunity_name",
    "opportunity_provider",
    "opportunity_type",
    "full_name",
)


def _missing_fields(row: Testimonial) -> list[str]:
    missing = [field for field in _REQUIRED_FOR_SUBMISSION if not getattr(row, field)]
    if not row.outcome_narrative and not row.impact:
        missing.append("outcome_narrative_or_impact")
    return missing


async def submit(session: AsyncSession, *, user_id: str, testimonial_id: UUID, consent_confirmed: bool) -> Testimonial:
    row = await session.get(Testimonial, testimonial_id)
    if row is None or row.user_id != user_id:
        raise TestimonialError("not_found")
    if row.status not in (TestimonialStatus.draft, TestimonialStatus.changes_requested):
        raise TestimonialError("not_submittable")
    if not consent_confirmed:
        raise TestimonialError("consent_required")
    missing = _missing_fields(row)
    if missing:
        raise TestimonialError(f"missing_fields:{','.join(missing)}")

    previous = row.status
    now = utc_now()
    row.status = TestimonialStatus.submitted
    row.submitted_at = now
    row.consent_confirmed_at = now
    row.rejection_reason = None
    session.add(
        TestimonialModerationHistory(
            testimonial_id=row.id,
            previous_status=previous.value,
            new_status=row.status.value,
            actor_id=user_id,
            notes="Submitted for review by applicant.",
        )
    )
    await session.flush()
    await session.refresh(row)
    return row


async def withdraw(session: AsyncSession, *, user_id: str, testimonial_id: UUID) -> Testimonial:
    row = await session.get(Testimonial, testimonial_id)
    if row is None or row.user_id != user_id:
        raise TestimonialError("not_found")
    if row.status == TestimonialStatus.withdrawn:
        return row
    if row.status == TestimonialStatus.draft:
        raise TestimonialError("nothing_to_withdraw")

    previous = row.status
    row.status = TestimonialStatus.withdrawn
    row.withdrawn_at = utc_now()
    session.add(
        TestimonialModerationHistory(
            testimonial_id=row.id,
            previous_status=previous.value,
            new_status=row.status.value,
            actor_id=user_id,
            notes="Withdrawn by applicant.",
        )
    )
    await session.flush()
    await session.refresh(row)
    return row


async def _transition(
    session: AsyncSession,
    *,
    row: Testimonial,
    actor_id: str,
    new_status: TestimonialStatus,
    allowed_from: tuple[TestimonialStatus, ...],
    notes: str,
    timestamp_field: str | None = None,
) -> Testimonial:
    if row.status not in allowed_from:
        raise TestimonialError("invalid_transition")
    previous = row.status
    row.status = new_status
    row.last_moderator_id = actor_id
    if timestamp_field:
        setattr(row, timestamp_field, utc_now())
    session.add(
        TestimonialModerationHistory(
            testimonial_id=row.id,
            previous_status=previous.value,
            new_status=new_status.value,
            actor_id=actor_id,
            notes=notes,
        )
    )
    await session.flush()
    await session.refresh(row)
    return row


_UNDER_STAFF_REVIEW = (TestimonialStatus.submitted, TestimonialStatus.under_review)


async def approve(session: AsyncSession, *, actor_id: str, row: Testimonial, notes: str) -> Testimonial:
    row.rejection_reason = None
    return await _transition(
        session,
        row=row,
        actor_id=actor_id,
        new_status=TestimonialStatus.approved,
        allowed_from=_UNDER_STAFF_REVIEW,
        notes=notes,
        timestamp_field="approved_at",
    )


async def reject(session: AsyncSession, *, actor_id: str, row: Testimonial, reason: str) -> Testimonial:
    row.rejection_reason = reason
    return await _transition(
        session,
        row=row,
        actor_id=actor_id,
        new_status=TestimonialStatus.rejected,
        allowed_from=_UNDER_STAFF_REVIEW,
        notes=reason,
        timestamp_field="rejected_at",
    )


async def request_changes(session: AsyncSession, *, actor_id: str, row: Testimonial, reason: str) -> Testimonial:
    row.rejection_reason = reason
    return await _transition(
        session,
        row=row,
        actor_id=actor_id,
        new_status=TestimonialStatus.changes_requested,
        allowed_from=_UNDER_STAFF_REVIEW,
        notes=reason,
    )


async def mark_under_review(session: AsyncSession, *, actor_id: str, row: Testimonial) -> Testimonial:
    return await _transition(
        session,
        row=row,
        actor_id=actor_id,
        new_status=TestimonialStatus.under_review,
        allowed_from=(TestimonialStatus.submitted,),
        notes="Picked up for review.",
    )


async def archive(session: AsyncSession, *, actor_id: str, row: Testimonial, reason: str) -> Testimonial:
    """Staff-initiated hide - reuses the `withdrawn` status (never a
    separate `archived` one) so "no longer public" has exactly one
    meaning regardless of who triggered it; the moderation-history note
    distinguishes an admin archive from an applicant's own withdrawal.
    """
    return await _transition(
        session,
        row=row,
        actor_id=actor_id,
        new_status=TestimonialStatus.withdrawn,
        allowed_from=(TestimonialStatus.approved, TestimonialStatus.rejected, TestimonialStatus.under_review),
        notes=f"Archived by staff: {reason}",
        timestamp_field="withdrawn_at",
    )


async def verify(
    session: AsyncSession,
    *,
    actor_id: str,
    row: Testimonial,
    verification_method: str,
    notes: str | None,
) -> Testimonial:
    """Only ever callable by an authorized moderator/administrator (see
    the route's permission dependency) - this is the one place
    `verification_status` can move to `verified`, keeping the "Verified"
    badge meaningful (Phase 33: "verification meaningless" is exactly
    what this guards against).
    """
    if row.status not in (TestimonialStatus.approved, TestimonialStatus.under_review, TestimonialStatus.submitted):
        raise TestimonialError("cannot_verify_unreviewed_story")
    row.verification_status = TestimonialVerificationStatus.verified
    row.verified_at = utc_now()
    row.verified_by = actor_id
    row.verification_method = verification_method
    row.last_moderator_id = actor_id
    session.add(
        TestimonialModerationHistory(
            testimonial_id=row.id,
            previous_status=row.status.value,
            new_status=row.status.value,
            actor_id=actor_id,
            notes=f"Verified via {verification_method}." + (f" {notes}" if notes else ""),
        )
    )
    await session.flush()
    await session.refresh(row)
    return row


async def set_featured(session: AsyncSession, *, actor_id: str, row: Testimonial, featured: bool) -> Testimonial:
    if featured and row.status != TestimonialStatus.approved:
        raise TestimonialError("only_approved_can_be_featured")
    row.featured = featured
    row.last_moderator_id = actor_id
    session.add(
        TestimonialModerationHistory(
            testimonial_id=row.id,
            previous_status=row.status.value,
            new_status=row.status.value,
            actor_id=actor_id,
            notes="Featured by staff." if featured else "Unfeatured by staff.",
        )
    )
    await session.flush()
    await session.refresh(row)
    return row


async def set_internal_notes(
    session: AsyncSession, *, actor_id: str, row: Testimonial, notes: str
) -> Testimonial:
    """Overwrites the staff-only working notes - no history entry, since
    this is a free-form scratchpad for moderators, not itself a
    reviewable decision (unlike approve/reject/verify, which always do
    write history).
    """
    row.internal_notes = notes or None
    row.last_moderator_id = actor_id
    await session.flush()
    await session.refresh(row)
    return row


async def record_view(session: AsyncSession, *, row: Testimonial) -> None:
    row.view_count += 1
    await session.flush()


async def set_reaction(
    session: AsyncSession, *, user_id: str, row: Testimonial, reaction_type: TestimonialReactionType
) -> Testimonial:
    if row.status not in PUBLIC_STATUSES:
        raise TestimonialError("not_reactable")
    existing = await session.scalar(
        select(TestimonialReaction).where(
            TestimonialReaction.testimonial_id == row.id,
            TestimonialReaction.user_id == user_id,
        )
    )
    counters = {
        TestimonialReactionType.helpful: "helpful_count",
        TestimonialReactionType.inspiring: "inspiring_count",
        TestimonialReactionType.useful: "useful_count",
    }
    if existing is not None:
        if existing.reaction_type == reaction_type:
            return row
        setattr(row, counters[existing.reaction_type], max(0, getattr(row, counters[existing.reaction_type]) - 1))
        existing.reaction_type = reaction_type
    else:
        session.add(TestimonialReaction(testimonial_id=row.id, user_id=user_id, reaction_type=reaction_type))
    setattr(row, counters[reaction_type], getattr(row, counters[reaction_type]) + 1)
    await session.flush()
    await session.refresh(row)
    return row


async def remove_reaction(session: AsyncSession, *, user_id: str, row: Testimonial) -> Testimonial:
    existing = await session.scalar(
        select(TestimonialReaction).where(
            TestimonialReaction.testimonial_id == row.id,
            TestimonialReaction.user_id == user_id,
        )
    )
    if existing is None:
        return row
    counters = {
        TestimonialReactionType.helpful: "helpful_count",
        TestimonialReactionType.inspiring: "inspiring_count",
        TestimonialReactionType.useful: "useful_count",
    }
    field = counters[existing.reaction_type]
    setattr(row, field, max(0, getattr(row, field) - 1))
    await session.delete(existing)
    await session.flush()
    await session.refresh(row)
    return row


async def public_stats(session: AsyncSession) -> dict[str, int | None]:
    """Real aggregates only - a metric with zero real rows behind it is
    `None` (hidden), never a fabricated placeholder (Phase 3).
    """
    base = select(func.count(Testimonial.id)).where(Testimonial.status.in_(PUBLIC_STATUSES))
    total = await session.scalar(base) or 0
    verified = (
        await session.scalar(
            base.where(Testimonial.verification_status == TestimonialVerificationStatus.verified)
        )
        or 0
    )
    countries = await session.scalar(
        select(func.count(func.distinct(Testimonial.country))).where(
            Testimonial.status.in_(PUBLIC_STATUSES), Testimonial.country.is_not(None)
        )
    ) or 0
    types_ = await session.scalar(
        select(func.count(func.distinct(Testimonial.opportunity_type))).where(
            Testimonial.status.in_(PUBLIC_STATUSES)
        )
    ) or 0
    fields_ = await session.scalar(
        select(func.count(func.distinct(Testimonial.field_of_study))).where(
            Testimonial.status.in_(PUBLIC_STATUSES), Testimonial.field_of_study.is_not(None)
        )
    ) or 0
    return {
        "total_stories": total or None,
        "verified_stories": verified or None,
        "countries_represented": countries or None,
        "opportunity_types_represented": types_ or None,
        "fields_of_study_represented": fields_ or None,
    }
