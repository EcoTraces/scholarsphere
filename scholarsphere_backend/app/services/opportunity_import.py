import logging
from typing import Any
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ExternalOpportunity,
    OpportunitySource,
    RawExternalOpportunity,
    VerificationHistory,
    VerificationReview,
)
from app.models.external_opportunity import (
    ProcessingStatus,
    PublicationStatus,
    VerificationStatus,
)
from app.schemas.external_opportunity import (
    ImportStatistics,
    NormalizedExternalOpportunity,
)
from app.services.audit import append_audit
from app.services.parsing import duplicate_fingerprint, payload_hash, utc_now
from app.services.source_registry import seed_opportunity_sources

logger = logging.getLogger(__name__)


class ImportConflict(Exception):
    """A safe import-state conflict suitable for an HTTP 409 response."""

MATERIAL_FIELDS = frozenset(
    {
        "title",
        "provider_name",
        "deadline",
        "official_source_url",
        "official_application_url",
        "award_floor",
        "award_ceiling",
        "opportunity_status",
    }
)

PERSISTED_FIELDS = (
    "external_reference",
    "title",
    "opportunity_type",
    "provider_name",
    "provider_code",
    "country",
    "description",
    "opening_date",
    "deadline",
    "opportunity_status",
    "funding_type",
    "award_floor",
    "award_ceiling",
    "currency",
    "official_source_url",
    "official_application_url",
)


async def import_opportunities(
    session: AsyncSession,
    records: list[NormalizedExternalOpportunity | dict[str, Any]],
    *,
    source_code: str,
    actor_id: str,
    correlation_id: str | None = None,
    task_id: str | None = None,
) -> ImportStatistics:
    statistics = ImportStatistics(records_received=len(records))
    correlation_id = correlation_id or str(uuid4())

    async with session.begin():
        sources = await seed_opportunity_sources(session)
        source = sources.get(source_code)
        if source is None:
            raise ValueError(f"Unsupported opportunity source: {source_code}")
        if not source.is_active:
            raise ImportConflict("The external source is inactive.")

        for candidate in records:
            raw_payload = _raw_payload(candidate)
            external_id = _external_id(candidate, raw_payload)
            try:
                async with session.begin_nested():
                    normalized = _validate(candidate, source_code)
                    outcome = await _import_one(
                        session,
                        source,
                        normalized,
                        correlation_id=correlation_id,
                        actor_id=actor_id,
                    )
                setattr(
                    statistics,
                    f"records_{outcome}",
                    getattr(statistics, f"records_{outcome}") + 1,
                )
                logger.info(
                    "record_%s source_code=%s task_id=%s correlation_id=%s "
                    "external_id=%s record_count=1",
                    outcome,
                    source_code,
                    task_id or "manual",
                    correlation_id,
                    normalized.external_id,
                )
                if outcome != "skipped" and await _is_duplicate_candidate(
                    session, source.id, normalized
                ):
                    statistics.duplicate_candidates += 1
                    logger.warning(
                        "duplicate_detected source_code=%s task_id=%s "
                        "correlation_id=%s external_id=%s record_count=1",
                        source_code,
                        task_id or "manual",
                        correlation_id,
                        normalized.external_id,
                    )
            except Exception as error:
                statistics.records_failed += 1
                logger.info(
                    "parsing_failure source_code=%s task_id=%s correlation_id=%s "
                    "external_id=%s record_count=1",
                    source_code,
                    task_id or "manual",
                    correlation_id,
                    external_id or "unknown",
                )
                if external_id and raw_payload:
                    async with session.begin_nested():
                        await _record_failure(
                            session,
                            source,
                            external_id,
                            raw_payload,
                            _safe_record_error(error),
                        )
    return statistics


def _validate(
    candidate: NormalizedExternalOpportunity | dict[str, Any],
    source_code: str,
) -> NormalizedExternalOpportunity:
    normalized = (
        candidate
        if isinstance(candidate, NormalizedExternalOpportunity)
        else NormalizedExternalOpportunity.model_validate(candidate)
    )
    if normalized.source_code != source_code:
        raise ValueError("Record source does not match the requested import source")
    return normalized


async def _import_one(
    session: AsyncSession,
    source: OpportunitySource,
    normalized: NormalizedExternalOpportunity,
    *,
    correlation_id: str,
    actor_id: str,
) -> str:
    digest = payload_hash(normalized.raw_payload)
    raw = await session.scalar(
        select(RawExternalOpportunity).where(
            RawExternalOpportunity.source_id == source.id,
            RawExternalOpportunity.external_id == normalized.external_id,
        )
    )
    if raw is not None and raw.payload_hash == digest:
        raw.processing_status = ProcessingStatus.skipped
        raw.processing_error = None
        return "skipped"

    if raw is None:
        raw = RawExternalOpportunity(
            source_id=source.id,
            external_id=normalized.external_id,
            raw_payload=normalized.raw_payload,
            payload_hash=digest,
            collected_at=normalized.collected_at,
            processing_status=ProcessingStatus.pending,
        )
        session.add(raw)
    else:
        raw.raw_payload = normalized.raw_payload
        raw.payload_hash = digest
        raw.collected_at = normalized.collected_at
        raw.processing_status = ProcessingStatus.pending
        raw.processing_error = None

    opportunity = await session.scalar(
        select(ExternalOpportunity).where(
            ExternalOpportunity.source_id == source.id,
            ExternalOpportunity.external_id == normalized.external_id,
        )
    )
    fingerprint = duplicate_fingerprint(
        normalized.title, normalized.provider_name, normalized.deadline
    )
    values = _persistence_values(normalized)
    now = utc_now()
    material_changes: set[str] = set()
    if opportunity is None:
        opportunity = ExternalOpportunity(
            source_id=source.id,
            external_id=normalized.external_id,
            payload_hash=digest,
            external_fingerprint=fingerprint,
            duplicate_review_required=False,
            verification_status=VerificationStatus.pending,
            publication_status=PublicationStatus.unpublished,
            collected_at=normalized.collected_at,
            last_external_update_at=now,
            **values,
        )
        session.add(opportunity)
        await session.flush()
        session.add(VerificationReview(opportunity_id=opportunity.id))
        action = "created"
        previous_value = None
    else:
        previous_value = _snapshot(opportunity)
        changed_fields = {
            key: {"old": previous_value[key], "new": _json_value(value)}
            for key, value in values.items()
            if previous_value[key] != _json_value(value)
        }
        material_changes = set(changed_fields).intersection(MATERIAL_FIELDS)
        previous_status = opportunity.verification_status.value
        for key, value in values.items():
            setattr(opportunity, key, value)
        opportunity.payload_hash = digest
        opportunity.external_fingerprint = fingerprint
        opportunity.collected_at = normalized.collected_at
        opportunity.last_external_update_at = now
        if material_changes and previous_status not in {
            VerificationStatus.pending.value,
            VerificationStatus.reverification_required.value,
        }:
            opportunity.verification_status = VerificationStatus.reverification_required
            session.add(
                VerificationHistory(
                    opportunity_id=opportunity.id,
                    previous_status=previous_status,
                    new_status=VerificationStatus.reverification_required.value,
                    reason="Material external source fields changed.",
                    changed_fields={
                        key: changed_fields[key] for key in material_changes
                    },
                )
            )
            logger.warning(
                "reverification_required source_code=%s correlation_id=%s "
                "external_id=%s record_count=1",
                normalized.source_code,
                correlation_id,
                normalized.external_id,
            )
        action = "updated"

    duplicate = await session.scalar(
        select(ExternalOpportunity).where(
            ExternalOpportunity.external_fingerprint == fingerprint,
            ExternalOpportunity.source_id != source.id,
        )
    )
    if duplicate is not None:
        opportunity.duplicate_review_required = True
        duplicate.duplicate_review_required = True

    raw.opportunity_id = opportunity.id
    raw.processing_status = ProcessingStatus.imported
    append_audit(
        session,
        opportunity_id=opportunity.id,
        actor_id=actor_id,
        action=f"external_import_{action}",
        entity_type="external_opportunity",
        entity_id=opportunity.id,
        previous_value=previous_value,
        new_value=_snapshot(opportunity),
        correlation_id=correlation_id,
    )
    if duplicate is not None:
        append_audit(
            session,
            opportunity_id=opportunity.id,
            actor_id=actor_id,
            action="duplicate_detected",
            entity_type="external_opportunity",
            entity_id=opportunity.id,
            new_value={"candidate_opportunity_id": str(duplicate.id)},
            correlation_id=correlation_id,
        )
    if action == "updated" and material_changes:
        append_audit(
            session,
            opportunity_id=opportunity.id,
            actor_id=actor_id,
            action="material_external_change",
            entity_type="external_opportunity",
            entity_id=opportunity.id,
            previous_value=previous_value,
            new_value=_snapshot(opportunity),
            correlation_id=correlation_id,
        )
        if opportunity.verification_status == VerificationStatus.reverification_required:
            append_audit(
                session,
                opportunity_id=opportunity.id,
                actor_id=actor_id,
                action="reverification_required",
                entity_type="external_opportunity",
                entity_id=opportunity.id,
                correlation_id=correlation_id,
            )
    return action


async def _is_duplicate_candidate(
    session: AsyncSession,
    source_id: Any,
    normalized: NormalizedExternalOpportunity,
) -> bool:
    fingerprint = duplicate_fingerprint(
        normalized.title, normalized.provider_name, normalized.deadline
    )
    return (
        await session.scalar(
            select(ExternalOpportunity.id).where(
                ExternalOpportunity.external_fingerprint == fingerprint,
                ExternalOpportunity.source_id != source_id,
            )
        )
        is not None
    )


async def _record_failure(
    session: AsyncSession,
    source: OpportunitySource,
    external_id: str,
    raw_payload: dict[str, Any],
    error: str,
) -> None:
    raw = await session.scalar(
        select(RawExternalOpportunity).where(
            RawExternalOpportunity.source_id == source.id,
            RawExternalOpportunity.external_id == external_id,
        )
    )
    values = {
        "raw_payload": raw_payload,
        "payload_hash": payload_hash(raw_payload),
        "collected_at": utc_now(),
        "processing_status": ProcessingStatus.failed,
        "processing_error": error[:2000],
    }
    if raw is None:
        session.add(
            RawExternalOpportunity(
                source_id=source.id,
                external_id=external_id,
                **values,
            )
        )
    else:
        for key, value in values.items():
            setattr(raw, key, value)


def _persistence_values(
    normalized: NormalizedExternalOpportunity,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in PERSISTED_FIELDS:
        value = getattr(normalized, field)
        result[field] = str(value) if field.endswith("_url") and value else value
    return result


def _snapshot(opportunity: ExternalOpportunity) -> dict[str, Any]:
    return {
        field: _json_value(getattr(opportunity, field)) for field in PERSISTED_FIELDS
    } | {
        "verification_status": opportunity.verification_status.value,
        "publication_status": opportunity.publication_status.value,
        "duplicate_review_required": opportunity.duplicate_review_required,
    }


def _json_value(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _raw_payload(
    candidate: NormalizedExternalOpportunity | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(candidate, NormalizedExternalOpportunity):
        return candidate.raw_payload
    payload = candidate.get("raw_payload") if isinstance(candidate, dict) else None
    return payload if isinstance(payload, dict) else {}


def _external_id(
    candidate: NormalizedExternalOpportunity | dict[str, Any],
    raw_payload: dict[str, Any],
) -> str:
    if isinstance(candidate, NormalizedExternalOpportunity):
        return candidate.external_id
    return str(candidate.get("external_id") or raw_payload.get("id") or "").strip()


def _safe_record_error(error: Exception) -> str:
    if isinstance(error, ValidationError):
        fields = sorted(
            {
                ".".join(str(part) for part in item["loc"])
                for item in error.errors()
            }
        )
        return "Schema validation failed for: " + ", ".join(fields)[:1500]
    if isinstance(error, ValueError):
        return "Record normalization or import validation failed."
    return "Record import failed due to an internal error."
