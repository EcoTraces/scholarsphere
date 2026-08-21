from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.recommendation_governance import RecommendationFeedbackType

_CATEGORY_WIRE_VALUES = {
    "bestMatches",
    "newlyPublished",
    "fullyFunded",
    "noApplicationFee",
    "closingSoon",
    "suitableForCountry",
    "suitableForDegree",
    "online",
    "noIelts",
    "undergraduate",
    "masters",
    "phd",
    "professional",
}

_LABEL_WIRE_VALUES = {
    "strongMatch",
    "possibleMatch",
    "requiresAdditionalInformation",
    "deadlineApproaching",
    "fullyFunded",
    "noApplicationFee",
    "recommendedForCountry",
    "recommendedForQualification",
    "newlyVerified",
    "sponsoredOpportunity",
}

_FEEDBACK_TYPE_WIRE_TO_MODEL: dict[str, RecommendationFeedbackType] = {
    "helpful": RecommendationFeedbackType.helpful,
    "notRelevant": RecommendationFeedbackType.notRelevant,
    "inappropriate": RecommendationFeedbackType.inappropriate,
    "dismissed": RecommendationFeedbackType.dismissed,
}
_FEEDBACK_TYPE_MODEL_TO_WIRE: dict[RecommendationFeedbackType, str] = {
    value: key for key, value in _FEEDBACK_TYPE_WIRE_TO_MODEL.items()
}


def feedback_type_from_wire(value: str) -> RecommendationFeedbackType:
    try:
        return _FEEDBACK_TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown recommendation feedback type: {value!r}") from error


def feedback_type_to_wire(value: RecommendationFeedbackType) -> str:
    return _FEEDBACK_TYPE_MODEL_TO_WIRE[value]


def _validate_categories(values: list[str]) -> list[str]:
    unknown = set(values) - _CATEGORY_WIRE_VALUES
    if unknown:
        raise ValueError(f"Unknown recommendation categories: {sorted(unknown)}")
    return values


def _validate_labels(values: list[str]) -> list[str]:
    unknown = set(values) - _LABEL_WIRE_VALUES
    if unknown:
        raise ValueError(f"Unknown recommendation labels: {sorted(unknown)}")
    return values


class PersonalizationControlsSave(BaseModel):
    behavioural_recommendations_enabled: bool = True
    preferred_countries: list[str] = Field(default_factory=list)
    opportunity_categories: list[str] = Field(default_factory=list)
    hidden_opportunity_ids: list[str] = Field(default_factory=list)

    @field_validator("opportunity_categories")
    @classmethod
    def _check_categories(cls, value: list[str]) -> list[str]:
        return _validate_categories(value)


class PersonalizationControlsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    behavioural_recommendations_enabled: bool
    preferred_countries: list[str]
    opportunity_categories: list[str]
    hidden_opportunity_ids: list[str]


class RecordHistoryRequest(BaseModel):
    opportunity_id: str = Field(min_length=1, max_length=255)
    score: int = Field(ge=0, le=100)
    labels: list[str] = Field(default_factory=list)
    generated_at: datetime
    host_country: str = Field(min_length=1, max_length=255)

    @field_validator("labels")
    @classmethod
    def _check_labels(cls, value: list[str]) -> list[str]:
        return _validate_labels(value)


class RecommendationHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: str
    score: int
    labels: list[str]
    generated_at: datetime
    host_country: str


class RecordFeedbackRequest(BaseModel):
    opportunity_id: str = Field(min_length=1, max_length=255)
    type: str
    comment: str | None = Field(default=None, max_length=5000)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        feedback_type_from_wire(value)
        return value


class RecommendationFeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: str
    type: RecommendationFeedbackType
    created_at: datetime
    comment: str | None

    @field_serializer("type")
    def _serialize_type(self, value: RecommendationFeedbackType, _info: Any) -> str:
        return feedback_type_to_wire(value)


class RecommendationQualityReportRead(BaseModel):
    generated_count: int
    dismissal_rate: float
    helpful_rate: float
    country_diversity: int
    sponsored_share: float
    inappropriate_reports: int
