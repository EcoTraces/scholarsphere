import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class RecommendationFeedbackType(str, enum.Enum):
    helpful = "helpful"
    notRelevant = "notRelevant"
    inappropriate = "inappropriate"
    dismissed = "dismissed"


class PersonalizationControls(Base):
    __tablename__ = "personalization_controls"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    behavioural_recommendations_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    preferred_countries: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    opportunity_categories: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    hidden_opportunity_ids: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecommendationHistoryEntry(Base):
    __tablename__ = "recommendation_history_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    opportunity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    labels: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    host_country: Mapped[str] = mapped_column(String(255), nullable=False)


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    opportunity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[RecommendationFeedbackType] = mapped_column(
        Enum(RecommendationFeedbackType, native_enum=False), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
