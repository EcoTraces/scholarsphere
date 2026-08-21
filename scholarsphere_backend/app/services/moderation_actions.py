from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external_opportunity import ExternalOpportunity
from app.models.external_opportunity import VerificationStatus as OpportunityVerificationStatus
from app.models.moderation import (
    CLOSED_STATUSES,
    ModerationCase,
    ModerationHistoryEntry,
    ModerationStatus,
    ReportedEntityType,
)
from app.models.provider import Provider, ProviderStatus


def _entity_uuid(entity_id: str) -> UUID | None:
    """Opportunity/provider entity_ids are always real UUIDs (validated at

    submit time); ``user`` entity_ids are Firebase uids and never reach
    here. Parsed explicitly rather than relying on implicit string-to-UUID
    coercion, which isn't reliably portable across SQLite (tests) and
    Postgres (production).
    """
    try:
        return UUID(entity_id)
    except ValueError:
        return None


async def apply_transition(
    session: AsyncSession,
    case: ModerationCase,
    *,
    actor_id: str,
    status: ModerationStatus,
    notes: str,
    hide_content: bool = False,
) -> None:
    """Port of DemoModerationRepository.transition() + _applyAction().

    Mutates ``case`` in place, appends a history row, and applies the real
    side effect on the reported entity (ExternalOpportunity or Provider)
    when the status/hide_content combination calls for one. Shared by the
    assign, transition, and issueWarning routes so the side-effect logic
    exists in exactly one place.
    """
    case.status = status
    case.assigned_moderator_id = case.assigned_moderator_id or actor_id
    case.moderation_notes = notes
    case.temporarily_hidden = hide_content or case.temporarily_hidden
    session.add(
        ModerationHistoryEntry(
            case_id=case.id,
            status=status,
            actor_id=actor_id,
            notes=notes,
        )
    )

    if case.entity_type == ReportedEntityType.opportunity and (
        hide_content or status == ModerationStatus.content_removed
    ):
        entity_uuid = _entity_uuid(case.entity_id)
        opportunity = (
            await session.get(ExternalOpportunity, entity_uuid)
            if entity_uuid is not None
            else None
        )
        if opportunity is not None:
            opportunity.verification_status = (
                OpportunityVerificationStatus.archived
                if status == ModerationStatus.content_removed
                else OpportunityVerificationStatus.suspicious
            )

    if (
        case.entity_type == ReportedEntityType.provider
        and status == ModerationStatus.provider_suspended
    ):
        entity_uuid = _entity_uuid(case.entity_id)
        provider = await session.get(Provider, entity_uuid) if entity_uuid is not None else None
        if provider is not None:
            provider.status = ProviderStatus.suspended
            provider.permissions = []
            provider.review_note = case.moderation_notes or ""


def is_closed(status: ModerationStatus) -> bool:
    return status in CLOSED_STATUSES
