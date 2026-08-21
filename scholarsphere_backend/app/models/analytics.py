import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class OpportunityViewEvent(Base):
    __tablename__ = "opportunity_view_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("external_opportunities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
