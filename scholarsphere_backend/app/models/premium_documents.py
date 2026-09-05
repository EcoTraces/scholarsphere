import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class DocumentKind(str, enum.Enum):
    cv_academic = "cv_academic"
    cv_professional = "cv_professional"
    cv_scholarship = "cv_scholarship"
    sop = "sop"
    personal_statement = "personal_statement"
    motivation_letter = "motivation_letter"
    study_plan = "study_plan"
    research_proposal = "research_proposal"
    fellowship_leadership_statement = "fellowship_leadership_statement"
    fellowship_personal_statement = "fellowship_personal_statement"
    fellowship_impact_statement = "fellowship_impact_statement"
    fellowship_essay = "fellowship_essay"


class PremiumDocument(Base):
    """One row per document an applicant is building (a CV, an SOP, a study

    plan, ...). ``workspace_id`` is nullable because some document kinds
    (e.g. a general-purpose CV) are reusable across several tracked
    opportunities, not tied to one - matching how a real applicant keeps
    one CV and tailors cover material per application.
    """

    __tablename__ = "premium_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("premium_workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[DocumentKind] = mapped_column(Enum(DocumentKind, native_enum=False), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    latest_version_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PremiumDocumentVersion(Base):
    """Append-only version history - "never silently overwrite user

    content" is enforced structurally: an edit always inserts a new row
    with ``version_number = latest_version_number + 1`` rather than
    updating an existing one (see app/services/document_versioning.py).
    ``content`` holds the document's structured section data (the actual
    shape depends on ``PremiumDocument.kind`` - validated at the schema
    layer, app/schemas/premium_documents.py); rendered PDF/DOCX output is
    generated on demand from ``content``, never stored.
    """

    __tablename__ = "premium_document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "version_number", name="uq_premium_document_version_number"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("premium_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    content: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ats_analysis: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_analysis: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
