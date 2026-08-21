from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

_FEATURE_FLAGS = {
    "whatsappNotifications",
    "aiRecommendations",
    "automatedCollection",
    "providerSelfPublication",
    "premiumSubscription",
    "documentAnalysis",
    "newMobileFeatures",
    "experimentalSearch",
}

DEFAULT_FEATURE_FLAGS: dict[str, bool] = {flag: False for flag in _FEATURE_FLAGS}


class SaveConfigurationRequest(BaseModel):
    platform_name: str = Field(min_length=1, max_length=255)
    logo_location: str = Field(min_length=1, max_length=1000)
    brand_primary_color: str = Field(min_length=1, max_length=16)
    email_sender_name: str = Field(min_length=1, max_length=255)
    email_sender_address: str = Field(min_length=1, max_length=320)
    verification_expiration_days: int = Field(ge=1)
    supported_countries: list[str] = Field(min_length=1)
    supported_languages: list[str] = Field(min_length=1)
    opportunity_categories: list[str] = Field(default_factory=list)
    document_types: list[str] = Field(default_factory=list)
    maximum_file_size_bytes: int = Field(ge=1024)
    applicant_registration_enabled: bool = True
    provider_registration_enabled: bool = True
    maintenance_mode: bool = False
    feature_flags: dict[str, bool] = Field(default_factory=lambda: dict(DEFAULT_FEATURE_FLAGS))
    environment: dict[str, Any] = Field(default_factory=dict)
    security_policy: dict[str, Any] = Field(default_factory=dict)
    recommendation_settings: dict[str, Any] = Field(default_factory=dict)
    fraud_rule_settings: dict[str, Any] = Field(default_factory=dict)
    integration_settings: dict[str, Any] = Field(default_factory=dict)
    notification_settings: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("feature_flags")
    @classmethod
    def _validate_flags(cls, value: dict[str, bool]) -> dict[str, bool]:
        unknown = set(value) - _FEATURE_FLAGS
        if unknown:
            raise ValueError(f"Unknown feature flags: {sorted(unknown)}")
        return value


class RollbackRequest(BaseModel):
    target_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=1000)


class PlatformConfigurationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    platform_name: str
    logo_location: str
    brand_primary_color: str
    email_sender_name: str
    email_sender_address: str
    verification_expiration_days: int
    supported_countries: list[str]
    supported_languages: list[str]
    opportunity_categories: list[str]
    document_types: list[str]
    maximum_file_size_bytes: int
    applicant_registration_enabled: bool
    provider_registration_enabled: bool
    maintenance_mode: bool
    feature_flags: dict[str, bool]
    environment: dict[str, Any]
    security_policy: dict[str, Any]
    recommendation_settings: dict[str, Any]
    fraud_rule_settings: dict[str, Any]
    integration_settings: dict[str, Any]
    notification_settings: dict[str, Any]
    updated_at: datetime | None
    updated_by: str
    change_reason: str
