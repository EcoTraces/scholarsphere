import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class DocumentType(str, enum.Enum):
    passport = "passport"
    curriculum_vitae = "curriculum_vitae"
    academic_transcript = "academic_transcript"
    degree_certificate = "degree_certificate"
    recommendation_letters = "recommendation_letters"
    motivation_letter = "motivation_letter"
    personal_statement = "personal_statement"
    research_proposal = "research_proposal"
    english_language_certificate = "english_language_certificate"
    work_experience_letter = "work_experience_letter"
    birth_certificate = "birth_certificate"
    portfolio = "portfolio"
    financial_documents = "financial_documents"


class ApplicantDocument(Base):
    """One row per (user, document type) - uploading a new file of a type

    already on file replaces the old row, matching
    DemoDocumentRepository.add()'s removeWhere+add semantics.

    ``storage_path`` is a Firebase Storage path
    (``applicant-documents/{uid}/{fileName}``), never an arbitrary
    client-supplied URL - validated server-side to be under the caller's
    own uid folder, same pattern as Provider's supporting documents.
    Personal documents are far more sensitive than provider registration
    paperwork, so ``storage.rules`` keeps this path strictly owner-only
    (no staff read access), unlike ``provider-documents/``.
    """

    __tablename__ = "applicant_documents"
    __table_args__ = (
        UniqueConstraint("user_id", "type", name="uq_applicant_document_user_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[DocumentType] = mapped_column(Enum(DocumentType, native_enum=False), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    shared_with_provider_ids: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
