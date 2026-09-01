from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.premium_billing import (
    BillingInterval,
    EntitlementStatus,
    PaymentStatus,
    RefundStatus,
)


class PremiumPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str
    price_cents: int
    currency: str
    billing_interval: BillingInterval
    features: list[str]
    is_active: bool
    sort_order: int


class PremiumPlanCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    price_cents: int = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    billing_interval: BillingInterval = BillingInterval.one_time
    features: list[str] = Field(default_factory=list, max_length=64)
    is_active: bool = True
    sort_order: int = 0


class PremiumPlanUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    price_cents: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    features: list[str] | None = Field(default=None, max_length=64)
    is_active: bool | None = None
    sort_order: int | None = None


class CheckoutRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=64)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    plan_id: UUID
    amount_cents: int
    currency: str
    status: PaymentStatus
    provider: str
    provider_transaction_id: str | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class CheckoutResponse(BaseModel):
    payment: PaymentRead
    client_secret: str | None = None
    checkout_url: str | None = None
    payment_public_key: str


class EntitlementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    feature_keys: list[str]
    status: EntitlementStatus
    granted_at: datetime
    expires_at: datetime | None


class MyPremiumStatusRead(BaseModel):
    is_premium: bool
    entitlement: EntitlementRead | None
    available_plans: list[PremiumPlanRead]


class RefundRequest(BaseModel):
    amount_cents: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=1000)


class RefundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    amount_cents: int
    reason: str
    status: RefundStatus
    created_at: datetime
    created_by: str


class UsageLimitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    feature: str
    plan_code: str | None
    limit_per_day: int | None
    limit_per_month: int | None


class UsageLimitUpsertRequest(BaseModel):
    feature: str = Field(min_length=1, max_length=64)
    plan_code: str | None = Field(default=None, max_length=64)
    limit_per_day: int | None = Field(default=None, gt=0)
    limit_per_month: int | None = Field(default=None, gt=0)


class AdminRevenueSummary(BaseModel):
    total_successful_payments: int
    total_revenue_cents: int
    total_refunded_cents: int
    currency: str
    active_entitlements: int
    failed_payments: int
