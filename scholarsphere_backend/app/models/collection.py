import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class CollectionSourceType(str, enum.Enum):
    manualAdministrator = "manualAdministrator"
    providerSubmission = "providerSubmission"
    officialApi = "officialApi"
    approvedRss = "approvedRss"
    structuredFeed = "structuredFeed"
    controlledWebCollection = "controlledWebCollection"
    userSubmission = "userSubmission"


class CollectionLedgerEntry(Base):
    __tablename__ = "collection_ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("external_opportunities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[CollectionSourceType] = mapped_column(
        Enum(CollectionSourceType, native_enum=False), nullable=False
    )
    source_location: Mapped[str] = mapped_column(Text, nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_by_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    automated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    approved_source: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(64), nullable=False)
