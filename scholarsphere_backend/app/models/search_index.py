import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class SearchIndexEntry(Base):
    """One row per indexed opportunity. ``data`` is the full Opportunity

    snapshot as sent by the Flutter client (camelCase keys, matching the
    Dart Opportunity class's fields exactly) - stored opaquely and
    returned as-is in search hits, since the index's job is to filter,
    score, and facet an already-materialized client snapshot, not to
    re-derive or validate its business fields.
    """

    __tablename__ = "search_index_entries"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)


class SearchHistoryEntry(Base):
    __tablename__ = "search_history_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False)
    searched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
