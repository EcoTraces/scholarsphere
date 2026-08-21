from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.legal_compliance import LegalPolicyType, LegalRequestStatus, LegalRequestType

_POLICY_TYPE_WIRE_TO_MODEL: dict[str, LegalPolicyType] = {
    "termsAndConditions": LegalPolicyType.terms_and_conditions,
    "privacyPolicy": LegalPolicyType.privacy_policy,
    "cookiePolicy": LegalPolicyType.cookie_policy,
    "acceptableUse": LegalPolicyType.acceptable_use,
    "providerAgreement": LegalPolicyType.provider_agreement,
    "contentPublishing": LegalPolicyType.content_publishing,
    "verificationDisclaimer": LegalPolicyType.verification_disclaimer,
    "fundingDisclaimer": LegalPolicyType.funding_disclaimer,
    "copyrightPolicy": LegalPolicyType.copyright_policy,
    "dataProcessingAgreement": LegalPolicyType.data_processing_agreement,
}
_POLICY_TYPE_MODEL_TO_WIRE: dict[LegalPolicyType, str] = {
    value: key for key, value in _POLICY_TYPE_WIRE_TO_MODEL.items()
}

_REQUEST_TYPE_WIRE_TO_MODEL: dict[str, LegalRequestType] = {
    "takedown": LegalRequestType.takedown,
    "complaint": LegalRequestType.complaint,
    "regulator": LegalRequestType.regulator,
    "courtOrder": LegalRequestType.court_order,
    "dataProtection": LegalRequestType.data_protection,
}
_REQUEST_TYPE_MODEL_TO_WIRE: dict[LegalRequestType, str] = {
    value: key for key, value in _REQUEST_TYPE_WIRE_TO_MODEL.items()
}

_REQUEST_STATUS_WIRE_TO_MODEL: dict[str, LegalRequestStatus] = {
    "submitted": LegalRequestStatus.submitted,
    "validated": LegalRequestStatus.validated,
    "inReview": LegalRequestStatus.in_review,
    "actioned": LegalRequestStatus.actioned,
    "rejected": LegalRequestStatus.rejected,
    "closed": LegalRequestStatus.closed,
}
_REQUEST_STATUS_MODEL_TO_WIRE: dict[LegalRequestStatus, str] = {
    value: key for key, value in _REQUEST_STATUS_WIRE_TO_MODEL.items()
}


def policy_type_from_wire(value: str) -> LegalPolicyType:
    try:
        return _POLICY_TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown legal policy type: {value!r}") from error


def policy_type_to_wire(value: LegalPolicyType) -> str:
    return _POLICY_TYPE_MODEL_TO_WIRE[value]


def request_type_from_wire(value: str) -> LegalRequestType:
    try:
        return _REQUEST_TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown legal request type: {value!r}") from error


def request_type_to_wire(value: LegalRequestType) -> str:
    return _REQUEST_TYPE_MODEL_TO_WIRE[value]


def request_status_from_wire(value: str) -> LegalRequestStatus:
    try:
        return _REQUEST_STATUS_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown legal request status: {value!r}") from error


def request_status_to_wire(value: LegalRequestStatus) -> str:
    return _REQUEST_STATUS_MODEL_TO_WIRE[value]


class PublishPolicyRequest(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    type: str
    version: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    effective_at: datetime
    requires_acceptance: bool = True
    material_change: bool = False

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        policy_type_from_wire(value)
        return value


class AcceptPolicyRequest(BaseModel):
    policy_id: str = Field(min_length=1, max_length=255)
    policy_version: str = Field(min_length=1, max_length=64)
    ip_address: str = Field(default="", max_length=64)


class SubmitLegalRequestRequest(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    type: str
    requester: str = Field(min_length=1, max_length=500)
    subject_entity_id: str = Field(default="", max_length=255)
    description: str = Field(min_length=1)
    evidence_locations: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        request_type_from_wire(value)
        return value


class SaveComplianceRecordRequest(BaseModel):
    framework: str = Field(min_length=1, max_length=255)
    obligation: str = Field(min_length=1)
    status: str = Field(min_length=1, max_length=64)
    owner: str = Field(min_length=1, max_length=255)
    review_due_at: datetime
    evidence_locations: list[str] = Field(default_factory=list, max_length=100)


class LegalPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: LegalPolicyType
    version: str
    title: str
    content: str
    effective_at: datetime
    published_at: datetime
    requires_acceptance: bool
    material_change: bool
    published_by: str

    @field_serializer("type")
    def _serialize_type(self, value: LegalPolicyType, _info: Any) -> str:
        return policy_type_to_wire(value)


class LegalRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: LegalRequestType
    requester: str
    subject_entity_id: str
    description: str
    evidence_locations: list[str]
    status: LegalRequestStatus
    created_at: datetime
    history: list[str]

    @field_serializer("type")
    def _serialize_type(self, value: LegalRequestType, _info: Any) -> str:
        return request_type_to_wire(value)

    @field_serializer("status")
    def _serialize_status(self, value: LegalRequestStatus, _info: Any) -> str:
        return request_status_to_wire(value)


class ComplianceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    framework: str
    obligation: str
    status: str
    owner: str
    review_due_at: datetime
    evidence_locations: list[str]
