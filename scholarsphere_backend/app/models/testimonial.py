import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class TestimonialStatus(str, enum.Enum):
    """Editorial workflow state - distinct from `verification_status`
    below. A story can be `approved` (publicly visible) without ever
    being `verified`: publication only requires passing basic content
    moderation, while verification is a separate, stronger claim that
    ScholarSphere staff actually checked supporting evidence. Collapsing
    the two would make "Verified" meaningless (see
    docs/AUTHORITATIVE_SOURCES.md's own verification-integrity precedent
    for external opportunities, which this mirrors).
    """

    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    changes_requested = "changes_requested"
    approved = "approved"
    rejected = "rejected"
    withdrawn = "withdrawn"


#: Public-facing statuses. Never leak `draft`/`submitted`/`under_review`/
#: `changes_requested`/`rejected` to unauthenticated or other users' story
#: listings - see Phase 16's "avoid exposing internal moderation states
#: publicly" requirement.
PUBLIC_STATUSES = frozenset({TestimonialStatus.approved})


class TestimonialVerificationStatus(str, enum.Enum):
    unverified = "unverified"
    verified = "verified"


class TestimonialDisplayMode(str, enum.Enum):
    full_name = "full_name"
    first_name_last_initial = "first_name_last_initial"
    anonymous = "anonymous"


class TestimonialOutcome(str, enum.Enum):
    """Deliberately not collapsed into a single "success" flag - Phase 6
    of the feature spec requires distinguishing exactly these outcomes.
    """

    applied = "applied"
    shortlisted = "shortlisted"
    interviewed = "interviewed"
    selected = "selected"
    awarded = "awarded"
    admitted = "admitted"
    funded = "funded"
    other = "other"


class TestimonialReactionType(str, enum.Enum):
    helpful = "helpful"
    inspiring = "inspiring"
    useful = "useful"


class Testimonial(Base):
    """An applicant-submitted success story, from private draft through
    public, possibly-verified, possibly-featured publication.

    Deliberately one table rather than the six the feature spec sketches
    (`testimonial_evidence`, `testimonial_media`, `testimonial_verification`
    as separate tables): evidence is reviewed holistically by a single
    moderator per submission, not file-by-file, so per-file review state
    would be unused structure. `evidence_storage_paths` and
    `photo_storage_path` are Firebase Storage paths only (see
    `storage.rules`'s `testimonial-evidence/` and `testimonial-photos/`
    entries) - the backend never handles file bytes, matching
    `ApplicantDocument`'s established pattern.

    ``opportunity_id`` links to a real, currently-tracked
    ``ExternalOpportunity`` when one matches (Phase 6's "link to the
    relevant opportunity if it still exists") but is nullable: most
    successful applicants used an opportunity this backend's own sources
    never carried (word of mouth, an old posting, a source not yet
    integrated), so ``opportunity_name``/``opportunity_provider``/
    ``opportunity_type`` are always captured as plain text snapshots
    regardless of whether a link exists.

    ``full_name`` is always stored (needed for moderation and for
    ``display_mode == full_name``); the *displayed* name for every other
    mode is computed at read time in the schema layer, never stored
    separately, so a later display-mode change can never leak a name a
    user chose to withhold.
    """

    __tablename__ = "testimonials"
    __table_args__ = (
        Index("ix_testimonials_status", "status"),
        Index("ix_testimonials_verification_status", "verification_status"),
        Index("ix_testimonials_featured", "featured"),
        Index("ix_testimonials_opportunity_id", "opportunity_id"),
        Index("ix_testimonials_user_id", "user_id"),
        Index("ix_testimonials_country", "country"),
        Index("ix_testimonials_success_year", "success_year"),
        Index("ix_testimonials_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("external_opportunities.id", ondelete="SET NULL"), nullable=True
    )
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # --- Step 1: the opportunity ---------------------------------------
    opportunity_name: Mapped[str] = mapped_column(String(500), nullable=False)
    opportunity_provider: Mapped[str] = mapped_column(String(512), nullable=False)
    opportunity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    country: Mapped[str | None] = mapped_column(String(255))
    degree_level: Mapped[str | None] = mapped_column(String(128))
    field_of_study: Mapped[str | None] = mapped_column(String(255))
    success_year: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[TestimonialOutcome] = mapped_column(
        Enum(TestimonialOutcome, native_enum=False), nullable=False
    )

    # --- Step 2: the experience (the seven case-study questions) -------
    challenge: Mapped[str | None] = mapped_column(Text)
    discovery_story: Mapped[str | None] = mapped_column(Text)
    preparation_story: Mapped[str | None] = mapped_column(Text)
    scholarsphere_help: Mapped[str | None] = mapped_column(Text)
    outcome_narrative: Mapped[str | None] = mapped_column(Text)
    impact: Mapped[str | None] = mapped_column(Text)
    advice: Mapped[str | None] = mapped_column(Text)
    features_used: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

    # --- Step 3: profile snapshot ---------------------------------------
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    university: Mapped[str | None] = mapped_column(String(255))
    program: Mapped[str | None] = mapped_column(String(255))
    photo_storage_path: Mapped[str | None] = mapped_column(String(1024))

    # --- Step 4: privacy --------------------------------------------------
    display_mode: Mapped[TestimonialDisplayMode] = mapped_column(
        Enum(TestimonialDisplayMode, native_enum=False),
        default=TestimonialDisplayMode.first_name_last_initial,
        nullable=False,
    )
    show_university: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_country: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_program: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_photo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Step 5: evidence (never public - see storage.rules) -----------
    evidence_storage_paths: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )

    # --- Step 7: consent --------------------------------------------------
    consent_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- Editorial + verification state ---------------------------------
    status: Mapped[TestimonialStatus] = mapped_column(
        Enum(TestimonialStatus, native_enum=False),
        default=TestimonialStatus.draft,
        nullable=False,
    )
    verification_status: Mapped[TestimonialVerificationStatus] = mapped_column(
        Enum(TestimonialVerificationStatus, native_enum=False),
        default=TestimonialVerificationStatus.unverified,
        nullable=False,
    )
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Shown to the applicant (rejected / changes_requested). Never confused
    # with `internal_notes`, which is staff-only and never serialized to
    # any applicant- or public-facing schema.
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    verified_by: Mapped[str | None] = mapped_column(String(255))
    verification_method: Mapped[str | None] = mapped_column(String(255))
    last_moderator_id: Mapped[str | None] = mapped_column(String(255))

    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inspiring_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    useful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    moderation_history: Mapped[list["TestimonialModerationHistory"]] = relationship(
        back_populates="testimonial",
        cascade="all, delete-orphan",
        order_by="TestimonialModerationHistory.created_at",
    )
    reactions: Mapped[list["TestimonialReaction"]] = relationship(
        back_populates="testimonial", cascade="all, delete-orphan"
    )


class TestimonialModerationHistory(Base):
    """Append-only moderation trail - mirrors
    `external_opportunity.VerificationHistory` exactly. Never mutated or
    deleted once written, so the record of who changed what and why
    survives even if `Testimonial.internal_notes` is later overwritten.
    """

    __tablename__ = "testimonial_moderation_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    testimonial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("testimonials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_status: Mapped[str] = mapped_column(String(64), nullable=False)
    new_status: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    testimonial: Mapped[Testimonial] = relationship(back_populates="moderation_history")


class TestimonialReaction(Base):
    """One row per (testimonial, user) - changing a reaction updates this
    row rather than adding another, enforcing the "one-reaction-per-user"
    rule at the schema level, not just in application code.
    """

    __tablename__ = "testimonial_reactions"
    __table_args__ = (
        UniqueConstraint("testimonial_id", "user_id", name="uq_testimonial_reaction_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    testimonial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("testimonials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reaction_type: Mapped[TestimonialReactionType] = mapped_column(
        Enum(TestimonialReactionType, native_enum=False), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    testimonial: Mapped[Testimonial] = relationship(back_populates="reactions")
