from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.external_opportunity import JSONType


class PlatformConfiguration(Base):
    __tablename__ = "platform_configurations"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_location: Mapped[str] = mapped_column(String(1000), nullable=False)
    brand_primary_color: Mapped[str] = mapped_column(String(16), nullable=False)
    email_sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email_sender_address: Mapped[str] = mapped_column(String(320), nullable=False)
    verification_expiration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    supported_countries: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    supported_languages: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    opportunity_categories: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    document_types: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    maximum_file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    applicant_registration_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provider_registration_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feature_flags: Mapped[dict[str, bool]] = mapped_column(JSONType, nullable=False)
    environment: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    security_policy: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    recommendation_settings: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    fraud_rule_settings: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    integration_settings: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    notification_settings: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    change_reason: Mapped[str] = mapped_column(String(1000), nullable=False)
