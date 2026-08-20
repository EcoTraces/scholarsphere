import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.applicant_document import DocumentType

_TYPE_WIRE_TO_MODEL: dict[str, DocumentType] = {
    "passport": DocumentType.passport,
    "curriculumVitae": DocumentType.curriculum_vitae,
    "academicTranscript": DocumentType.academic_transcript,
    "degreeCertificate": DocumentType.degree_certificate,
    "recommendationLetters": DocumentType.recommendation_letters,
    "motivationLetter": DocumentType.motivation_letter,
    "personalStatement": DocumentType.personal_statement,
    "researchProposal": DocumentType.research_proposal,
    "englishLanguageCertificate": DocumentType.english_language_certificate,
    "workExperienceLetter": DocumentType.work_experience_letter,
    "birthCertificate": DocumentType.birth_certificate,
    "portfolio": DocumentType.portfolio,
    "financialDocuments": DocumentType.financial_documents,
}
_TYPE_MODEL_TO_WIRE: dict[DocumentType, str] = {
    value: key for key, value in _TYPE_WIRE_TO_MODEL.items()
}

_STORAGE_PATH_RE = re.compile(r"^applicant-documents/(?P<uid>[^/]+)/(?P<file_name>[^/]+)$")


def type_from_wire(value: str) -> DocumentType:
    try:
        return _TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown document type: {value!r}") from error


def type_to_wire(value: DocumentType) -> str:
    return _TYPE_MODEL_TO_WIRE[value]


def document_owner_uid(storage_path: str) -> str | None:
    """Return the uid segment of an `applicant-documents/{uid}/{file}` path, or None."""
    match = _STORAGE_PATH_RE.match(storage_path)
    return match.group("uid") if match else None


class ApplicantDocumentCreate(BaseModel):
    type: str
    file_name: str = Field(min_length=1, max_length=500)
    storage_path: str = Field(min_length=1, max_length=1024)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        type_from_wire(value)
        return value

    @field_validator("storage_path")
    @classmethod
    def _validate_storage_path(cls, value: str) -> str:
        if not _STORAGE_PATH_RE.match(value):
            raise ValueError(
                "storage_path must be an 'applicant-documents/{uid}/{fileName}' "
                "Storage path, not an arbitrary URL or filename."
            )
        return value


class GrantProviderAccessRequest(BaseModel):
    provider_id: str = Field(min_length=1, max_length=255)


class ApplicantDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    type: DocumentType
    file_name: str
    uploaded_at: datetime
    shared_with_provider_ids: list[str]

    @field_serializer("type")
    def _serialize_type(self, value: DocumentType, _info: Any) -> str:
        return type_to_wire(value)
