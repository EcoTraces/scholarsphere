from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.privacy import ConsentType, PrivacyRequestStatus, PrivacyRequestType

_CONSENT_WIRE_TO_MODEL: dict[str, ConsentType] = {
    "privacyPolicy": ConsentType.privacy_policy,
    "termsAndConditions": ConsentType.terms_and_conditions,
    "cookies": ConsentType.cookies,
    "marketing": ConsentType.marketing,
    "notifications": ConsentType.notifications,
    "personalizedRecommendations": ConsentType.personalized_recommendations,
    "sensitiveData": ConsentType.sensitive_data,
    "documentStorage": ConsentType.document_storage,
    "thirdPartySharing": ConsentType.third_party_sharing,
}
_CONSENT_MODEL_TO_WIRE: dict[ConsentType, str] = {
    value: key for key, value in _CONSENT_WIRE_TO_MODEL.items()
}

_REQUEST_TYPE_WIRE_TO_MODEL: dict[str, PrivacyRequestType] = {
    "dataExport": PrivacyRequestType.data_export,
    "accountDeletion": PrivacyRequestType.account_deletion,
    "dataCorrection": PrivacyRequestType.data_correction,
    "documentDeletion": PrivacyRequestType.document_deletion,
}
_REQUEST_TYPE_MODEL_TO_WIRE: dict[PrivacyRequestType, str] = {
    value: key for key, value in _REQUEST_TYPE_WIRE_TO_MODEL.items()
}

_REQUEST_STATUS_WIRE_TO_MODEL: dict[str, PrivacyRequestStatus] = {
    "submitted": PrivacyRequestStatus.submitted,
    "inReview": PrivacyRequestStatus.in_review,
    "completed": PrivacyRequestStatus.completed,
    "rejected": PrivacyRequestStatus.rejected,
    "cancelled": PrivacyRequestStatus.cancelled,
}
_REQUEST_STATUS_MODEL_TO_WIRE: dict[PrivacyRequestStatus, str] = {
    value: key for key, value in _REQUEST_STATUS_WIRE_TO_MODEL.items()
}

_REQUIRED_LEGAL_CONSENTS = frozenset(
    {ConsentType.privacy_policy, ConsentType.terms_and_conditions}
)


def consent_type_from_wire(value: str) -> ConsentType:
    try:
        return _CONSENT_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown consent type: {value!r}") from error


def consent_type_to_wire(value: ConsentType) -> str:
    return _CONSENT_MODEL_TO_WIRE[value]


def is_required_legal_consent(value: ConsentType) -> bool:
    return value in _REQUIRED_LEGAL_CONSENTS


def request_type_from_wire(value: str) -> PrivacyRequestType:
    try:
        return _REQUEST_TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown privacy request type: {value!r}") from error


class GrantConsentRequest(BaseModel):
    type: str
    policy_version: str = Field(min_length=1, max_length=64)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        consent_type_from_wire(value)
        return value


class SubmitPrivacyRequest(BaseModel):
    type: str
    notes: str = Field(default="", max_length=5000)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        request_type_from_wire(value)
        return value


class RecordOrganizationAccessRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)
    organization_id: str = Field(min_length=1, max_length=255)
    organization_name: str = Field(min_length=1, max_length=512)
    data_categories: list[str] = Field(default_factory=list, max_length=50)


class RecordIncidentRequest(BaseModel):
    summary: str = Field(min_length=1, max_length=5000)
    affected_user_ids: list[str] = Field(default_factory=list, max_length=10000)


class ConsentRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    type: ConsentType
    policy_version: str
    granted_at: datetime
    withdrawn_at: datetime | None

    @field_serializer("type")
    def _serialize_type(self, value: ConsentType, _info: Any) -> str:
        return consent_type_to_wire(value)


class PrivacyRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    type: PrivacyRequestType
    status: PrivacyRequestStatus
    submitted_at: datetime
    completed_at: datetime | None
    notes: str

    @field_serializer("type")
    def _serialize_type(self, value: PrivacyRequestType, _info: Any) -> str:
        return _REQUEST_TYPE_MODEL_TO_WIRE[value]

    @field_serializer("status")
    def _serialize_status(self, value: PrivacyRequestStatus, _info: Any) -> str:
        return _REQUEST_STATUS_MODEL_TO_WIRE[value]


class OrganizationAccessRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    organization_id: str
    organization_name: str
    data_categories: list[str]
    accessed_at: datetime
    consent_record_type: ConsentType

    @field_serializer("consent_record_type")
    def _serialize_consent_type(self, value: ConsentType, _info: Any) -> str:
        return consent_type_to_wire(value)


class PrivacyIncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recorded_at: datetime
    summary: str
    affected_user_ids: list[str]
    resolved_at: datetime | None
