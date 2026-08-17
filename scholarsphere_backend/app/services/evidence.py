from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExternalOpportunity, RawExternalOpportunity
from app.schemas.opportunity_public import FieldEvidence, OpportunityEvidence
from app.services.eu_funding import _metadata_dict
from app.services.parsing import first_value


def _grants_gov_evidence(raw: dict) -> dict[str, object]:
    return {
        "title": raw.get("title"),
        "provider_name": raw.get("agencyName") or raw.get("agencyCode"),
        "opening_date": raw.get("openDate"),
        "deadline": raw.get("closeDate"),
        "opportunity_status": raw.get("oppStatus"),
    }


def _simpler_grants_evidence(raw: dict) -> dict[str, object]:
    return {
        "title": raw.get("opportunity_title"),
        "provider_name": raw.get("agency_name") or raw.get("agency_code"),
        "opening_date": raw.get("post_date"),
        "deadline": raw.get("close_date"),
        "opportunity_status": raw.get("opportunity_status"),
    }


def _eu_funding_evidence(raw: dict) -> dict[str, object]:
    metadata = _metadata_dict(raw.get("metadata")) or raw
    return {
        "title": first_value(metadata.get("title")),
        "provider_name": first_value(metadata.get("caName")),
        "opening_date": first_value(metadata.get("startDate")),
        "deadline": first_value(metadata.get("deadlineDate")),
        "opportunity_status": first_value(metadata.get("status")),
    }


EVIDENCE_EXTRACTORS = {
    "grants_gov": _grants_gov_evidence,
    "simpler_grants": _simpler_grants_evidence,
    "eu_funding_tenders": _eu_funding_evidence,
}


async def build_opportunity_evidence(
    session: AsyncSession, opportunity: ExternalOpportunity
) -> OpportunityEvidence:
    """Answer "where did this field come from?" with the exact raw source record.

    Shared by the applicant-facing (published-only) and verification-officer
    (any status) evidence endpoints so both surface identical, unmodified
    ground truth - never inferred or fabricated.
    """
    raw = await session.scalar(
        select(RawExternalOpportunity).where(
            RawExternalOpportunity.source_id == opportunity.source_id,
            RawExternalOpportunity.external_id == opportunity.external_id,
        )
    )
    raw_payload = raw.raw_payload if raw is not None else {}
    extractor = EVIDENCE_EXTRACTORS.get(opportunity.source.source_code)
    extracted = extractor(raw_payload) if extractor and raw_payload else {}
    field_evidence = [
        FieldEvidence(
            field=field_name,
            value=value,
            confidence="HIGH" if value not in (None, "") else "UNKNOWN",
        )
        for field_name, value in extracted.items()
    ]
    return OpportunityEvidence(
        opportunity_id=opportunity.id,
        source_code=opportunity.source.source_code,
        source_name=opportunity.source.source_name,
        source_type=opportunity.source.source_type,
        source_trust_level=opportunity.source.trust_level,
        official_source_url=opportunity.official_source_url,
        collected_at=opportunity.collected_at,
        field_evidence=field_evidence,
        raw_payload=raw_payload,
    )
