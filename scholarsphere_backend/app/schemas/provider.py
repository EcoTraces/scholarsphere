import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.provider import ProviderPermission, ProviderStatus

_STATUS_WIRE_TO_MODEL: dict[str, ProviderStatus] = {
    "draft": ProviderStatus.draft,
    "pendingReview": ProviderStatus.pending_review,
    "additionalInformationRequired": ProviderStatus.additional_information_required,
    "verified": ProviderStatus.verified,
    "rejected": ProviderStatus.rejected,
    "suspended": ProviderStatus.suspended,
    "verificationExpired": ProviderStatus.verification_expired,
    "archived": ProviderStatus.archived,
}
_STATUS_MODEL_TO_WIRE: dict[ProviderStatus, str] = {
    value: key for key, value in _STATUS_WIRE_TO_MODEL.items()
}

_PERMISSION_WIRE_TO_MODEL: dict[str, ProviderPermission] = {
    "manageOrganization": ProviderPermission.manage_organization,
    "publishOpportunities": ProviderPermission.publish_opportunities,
    "manageAdmins": ProviderPermission.manage_admins,
}
_PERMISSION_MODEL_TO_WIRE: dict[str, str] = {
    value.value: key for key, value in _PERMISSION_WIRE_TO_MODEL.items()
}

_DOCUMENT_PATH_RE = re.compile(r"^provider-documents/(?P<uid>[^/]+)/(?P<file_name>[^/]+)$")


def status_from_wire(value: str) -> ProviderStatus:
    try:
        return _STATUS_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown provider status: {value!r}") from error


def status_to_wire(value: ProviderStatus) -> str:
    return _STATUS_MODEL_TO_WIRE[value]


def permission_to_wire(value: str) -> str:
    return _PERMISSION_MODEL_TO_WIRE.get(value, value)


def document_owner_uid(path: str) -> str | None:
    """Return the uid segment of a `provider-documents/{uid}/{file}` path, or None."""
    match = _DOCUMENT_PATH_RE.match(path)
    return match.group("uid") if match else None


def _validate_document_path(path: str) -> str:
    if not _DOCUMENT_PATH_RE.match(path):
        raise ValueError(
            "Supporting documents must be a 'provider-documents/{uid}/{fileName}' "
            "Storage path, not an arbitrary URL or filename."
        )
    return path


class ProviderCreate(BaseModel):
    organization_name: str = Field(min_length=1, max_length=512)
    organization_type: str = Field(min_length=1, max_length=128)
    registration_number: str = Field(max_length=255)
    country: str = Field(min_length=1, max_length=255)
    official_website: str = Field(min_length=1, max_length=2048)
    official_email_domain: str = Field(min_length=1, max_length=255)
    physical_address: str = Field(min_length=1)
    contact_person: str = Field(min_length=1, max_length=255)
    contact_phone: str = Field(min_length=1, max_length=64)
    supporting_documents: list[str] = Field(default_factory=list, max_length=20)
    social_media_links: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("supporting_documents")
    @classmethod
    def _validate_documents(cls, value: list[str]) -> list[str]:
        return [_validate_document_path(item) for item in value]


class ProviderAdministratorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str
    email: str
    permissions: list[str]

    @field_serializer("permissions")
    def _serialize_permissions(self, permissions: list[str], _info: Any) -> list[str]:
        return [permission_to_wire(item) for item in permissions]


class ProviderActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    action: str
    actor_id: str
    occurred_at: datetime


class ProviderAppealRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reason: str
    submitted_at: datetime
    status: str


class ProviderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    organization_name: str
    organization_type: str
    registration_number: str
    country: str
    official_website: str
    official_email_domain: str
    physical_address: str
    contact_person: str
    contact_phone: str
    supporting_documents: list[str]
    social_media_links: list[str]
    status: ProviderStatus
    risk_score: int
    permissions: list[str]
    verification_date: datetime | None
    verified_by: str | None
    reverification_date: datetime | None
    review_note: str | None
    administrators: list[ProviderAdministratorRead] = Field(default_factory=list)
    activity_history: list[ProviderActivityRead] = Field(default_factory=list)
    appeals: list[ProviderAppealRead] = Field(default_factory=list)

    @field_serializer("status")
    def _serialize_status(self, status: ProviderStatus, _info: Any) -> str:
        return status_to_wire(status)

    @field_serializer("permissions")
    def _serialize_permissions(self, permissions: list[str], _info: Any) -> list[str]:
        return [permission_to_wire(item) for item in permissions]


class ProviderReviewRequest(BaseModel):
    decision: str
    official_email_verified: bool
    domain_verified: bool
    contact_verified: bool
    documents_verified: bool
    impersonation_check_passed: bool
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("decision")
    @classmethod
    def _validate_decision(cls, value: str) -> str:
        status_from_wire(value)
        return value

    @property
    def checklist_complete(self) -> bool:
        return all(
            [
                self.official_email_verified,
                self.domain_verified,
                self.contact_verified,
                self.documents_verified,
                self.impersonation_check_passed,
            ]
        )


class ProviderSuspendRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ProviderAppealRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ProviderAdministratorCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=320)
    permissions: list[str] = Field(default_factory=list, max_length=10)


class CanPublishResponse(BaseModel):
    can_publish: bool
