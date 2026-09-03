import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class PremiumFeature(str, enum.Enum):
    """Individually gateable premium capabilities. A `PremiumPlan.features`

    list is a list of these values (as strings) - the flagship "Complete
    Premium" plan lists all of them, but the architecture supports a future
    plan (e.g. "CV / ATS only") listing a subset without any code change
    beyond a new `PremiumPlan` row.
    """

    application_strategy = "application_strategy"
    requirement_matching = "requirement_matching"
    readiness_score = "readiness_score"
    personalized_checklist = "personalized_checklist"
    cv_builder = "cv_builder"
    ats_optimization = "ats_optimization"
    sop_builder = "sop_builder"
    study_plan_builder = "study_plan_builder"
    research_proposal_builder = "research_proposal_builder"
    fellowship_preparation = "fellowship_preparation"
    ai_document_improvement = "ai_document_improvement"
    document_versioning = "document_versioning"
    pdf_export = "pdf_export"
    docx_export = "docx_export"


class BillingInterval(str, enum.Enum):
    one_time = "one_time"
    monthly = "monthly"
    yearly = "yearly"


class PremiumPlan(Base):
    """Admin-configurable premium package - never a hardcoded price/feature

    list in application code. Seeded at startup with the flagship "Complete
    Premium Application Package" (see app/services/premium_plan_seed.py),
    but every field is editable via the admin routes afterward, and
    additional plans (e.g. "CV / ATS only") can be added the same way
    without a code change.
    """

    __tablename__ = "premium_plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    billing_interval: Mapped[BillingInterval] = mapped_column(
        Enum(BillingInterval, native_enum=False),
        default=BillingInterval.one_time,
        nullable=False,
    )
    features: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"
    refunded = "refunded"
    expired = "expired"
    disputed = "disputed"


TERMINAL_PAYMENT_STATUSES = frozenset(
    {
        PaymentStatus.success,
        PaymentStatus.failed,
        PaymentStatus.cancelled,
        PaymentStatus.refunded,
        PaymentStatus.expired,
    }
)


class Payment(Base):
    """One row per checkout attempt, created server-side before the

    applicant ever reaches the payment provider - see
    app/services/payment_service.py::initiate_checkout. `status` only ever
    moves forward via server-side verification (a provider webhook or an
    explicit verify call), never because a client request claims success.
    """

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("premium_plans.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False), default=PaymentStatus.pending, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_transaction_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_metadata: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PaymentEvent(Base):
    """One row per provider webhook/callback event actually processed.

    ``UniqueConstraint(provider, provider_event_id)`` is the real
    duplicate-webhook defense: a second delivery of the same event fails
    this constraint before any entitlement logic runs, rather than relying
    on application-level checking alone (Coding_Rules.md SS5's "maintain
    data integrity" rule) - the same pattern already used for
    ``uq_applicant_document_user_type`` and
    ``uq_application_user_opportunity`` elsewhere in this codebase.
    """

    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_payment_event_provider_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_result: Mapped[str] = mapped_column(String(64), default="", nullable=False)


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    trialing = "trialing"
    past_due = "past_due"
    canceled = "canceled"
    incomplete = "incomplete"


class Subscription(Base):
    """Not used by the one-time "Complete Premium" flagship package, but a

    real, working path for a future recurring plan - the
    PaymentProvider.createSubscription/cancelSubscription interface
    (app/services/payment_provider.py) is implemented and tested against
    this table now rather than bolted on later.
    """

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("premium_plans.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False),
        default=SubscriptionStatus.incomplete,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RefundStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RefundStatus] = mapped_column(
        Enum(RefundStatus, native_enum=False), default=RefundStatus.pending, nullable=False
    )
    provider_refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


class EntitlementStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    revoked = "revoked"


class Entitlement(Base):
    """The actual, server-authoritative grant of premium access - never a

    boolean flag. ``feature_keys`` snapshots the plan's features *at grant
    time*, so a later admin edit to a plan's feature list never silently
    changes what an already-paying user has access to (or doesn't).

    ``UniqueConstraint(source_payment_id)`` is the second half of this
    project's duplicate-webhook defense (the first half is
    ``PaymentEvent``'s own unique constraint): even if payment-event
    de-duplication were ever bypassed, a second attempt to grant an
    entitlement for the same payment fails this constraint rather than
    creating a duplicate grant.
    """

    __tablename__ = "entitlements"
    __table_args__ = (
        UniqueConstraint("source_payment_id", name="uq_entitlement_source_payment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("premium_plans.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    feature_keys: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    source_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[EntitlementStatus] = mapped_column(
        Enum(EntitlementStatus, native_enum=False),
        default=EntitlementStatus.active,
        nullable=False,
        index=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AIUsageStatus(str, enum.Enum):
    success = "success"
    failed = "failed"
    rate_limited = "rate_limited"
    quota_exceeded = "quota_exceeded"


class AIUsageRecord(Base):
    """One row per AI-generation request attempted (not just successes) -

    the basis for both the configurable usage-limit enforcement
    (app/services/usage_limits.py) and the admin "AI usage" dashboard.
    """

    __tablename__ = "ai_usage_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    feature: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[AIUsageStatus] = mapped_column(
        Enum(AIUsageStatus, native_enum=False), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class UsageLimit(Base):
    """Admin-configurable AI usage ceiling per feature - global by default

    (``plan_code`` null), or scoped to one plan by setting ``plan_code``.
    Both are actually enforced: ``check_usage_allowed``
    (app/services/usage_limits.py) looks up the caller's own active
    entitlements' plan codes and applies the most restrictive matching
    row, not just the global one.
    """

    __tablename__ = "usage_limits"
    __table_args__ = (
        UniqueConstraint("feature", "plan_code", name="uq_usage_limit_feature_plan"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    feature: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    limit_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


# Kept for readability at call sites that only need the float-cents
# conversion in one place.
def cents_to_amount(cents: int) -> float:
    return round(cents / 100, 2)
