from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ImportAuditLog


def append_audit(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str | UUID,
    correlation_id: str,
    actor_id: str | None = None,
    actor_role: str | None = None,
    opportunity_id: UUID | None = None,
    previous_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    result: str = "success",
) -> ImportAuditLog:
    entry = ImportAuditLog(
        opportunity_id=opportunity_id,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        result=result,
        previous_value=previous_value,
        new_value=new_value,
        correlation_id=correlation_id,
    )
    session.add(entry)
    return entry
