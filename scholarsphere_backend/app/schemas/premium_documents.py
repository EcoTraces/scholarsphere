from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.premium_documents import DocumentKind


class DocumentCreateRequest(BaseModel):
    kind: DocumentKind
    title: str = Field(min_length=1, max_length=500)
    workspace_id: UUID | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: DocumentKind
    title: str
    workspace_id: UUID | None
    latest_version_number: int
    created_at: datetime
    updated_at: datetime


class VersionCreateRequest(BaseModel):
    content: dict = Field(default_factory=dict)
    label: str = Field(default="", max_length=255)


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version_number: int
    label: str
    content: dict
    is_ai_generated: bool
    ats_score: float | None
    ats_analysis: dict | None
    quality_score: float | None
    quality_analysis: dict | None
    created_at: datetime
    created_by: str


class GenerateCvRequest(BaseModel):
    """CV content is built deterministically from the applicant's own

    background entries/profile (see document_generation.py); ``polish``
    opts into an AI wording pass over the summary and each entry's
    description, never adding new facts.
    """

    summary: str = Field(default="", max_length=2000)
    polish: bool = False


class GenerateNarrativeRequest(BaseModel):
    opportunity_id: UUID | None = None
    user_answers: dict[str, str] = Field(default_factory=dict)


class AtsAnalyzeResponse(BaseModel):
    score: float
    structure_score: float
    formatting_score: float
    readability_score: float
    keyword_score: float | None
    missing_sections: list[str]
    issues: list[str]
    strengths: list[str]
    disclaimer: str
