import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditChainState, AuditRecord, AuditResult
from app.services.parsing import utc_now

_GENESIS = "GENESIS"
_ANCHOR_ID = "global"

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_SECRET_RE = re.compile(r"(password|token|secret)=[^,\s}]+", re.IGNORECASE)
_LONG_NUMBER_RE = re.compile(r"\b\d{12,19}\b")


def _mask(value: str | None) -> str | None:
    if value is None:
        return None
    masked = _EMAIL_RE.sub("[masked-email]", value)
    masked = _SECRET_RE.sub(lambda match: f"{match.group(1)}=***", masked)
    masked = _LONG_NUMBER_RE.sub("[masked-number]", masked)
    return masked


def _mask_ip(value: str) -> str:
    parts = value.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    return value


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _fnv1a(value: str) -> str:
    data = value.encode("utf-8")
    hash_value = 0xCBF29CE484222325
    prime = 0x100000001B3
    mask = 0xFFFFFFFFFFFFFFFF
    for byte in data:
        hash_value ^= byte
        hash_value = (hash_value * prime) & mask
    return format(hash_value, "016x")


def _payload(
    previous_hash: str,
    actor_id: str,
    actor_role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    previous_value: str | None,
    new_value: str | None,
    timestamp: datetime,
    result: str,
    correlation_id: str,
) -> str:
    return "|".join(
        [
            previous_hash,
            actor_id,
            actor_role,
            action,
            entity_type,
            entity_id,
            previous_value or "",
            new_value or "",
            _aware(timestamp).isoformat(),
            result,
            correlation_id,
        ]
    )


async def _anchor(session: AsyncSession) -> AuditChainState:
    state = await session.get(AuditChainState, _ANCHOR_ID)
    if state is None:
        state = AuditChainState(id=_ANCHOR_ID, anchor=_GENESIS)
        session.add(state)
        await session.flush()
    return state


async def append_audit_record(
    session: AsyncSession,
    *,
    actor_id: str,
    actor_role: str,
    action: AuditAction,
    entity_type: str,
    entity_id: str,
    result: AuditResult,
    correlation_id: str,
    previous_value: str | None = None,
    new_value: str | None = None,
    ip_address: str = "",
    device_information: str = "",
    location_information: str = "",
    failure_reason: str | None = None,
) -> AuditRecord:
    """Appends a hash-chained, PII-masked audit record. Mirrors
    DemoAuditRepository.append exactly (masking then hashing over the
    masked values), including chain continuity across `enforce_retention`
    purges via the persisted `AuditChainState` anchor.
    """
    state = await _anchor(session)
    last = await session.scalar(
        select(AuditRecord).order_by(AuditRecord.id.desc()).limit(1)
    )
    previous_hash = last.integrity_hash if last is not None else state.anchor
    masked_previous = _mask(previous_value)
    masked_new = _mask(new_value)
    timestamp = utc_now()
    payload = _payload(
        previous_hash,
        actor_id,
        actor_role,
        action.value,
        entity_type,
        entity_id,
        masked_previous,
        masked_new,
        timestamp,
        result.value,
        correlation_id,
    )
    record = AuditRecord(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_value=masked_previous,
        new_value=masked_new,
        ip_address=_mask_ip(ip_address),
        device_information=device_information,
        location_information=location_information,
        timestamp=timestamp,
        result=result,
        failure_reason=_mask(failure_reason),
        correlation_id=correlation_id,
        integrity_hash=_fnv1a(payload),
    )
    session.add(record)
    await session.flush()
    return record


async def verify_integrity(session: AsyncSession) -> bool:
    state = await _anchor(session)
    previous_hash = state.anchor
    records = (
        await session.scalars(select(AuditRecord).order_by(AuditRecord.id.asc()))
    ).all()
    for record in records:
        payload = _payload(
            previous_hash,
            record.actor_id,
            record.actor_role,
            record.action.value,
            record.entity_type,
            record.entity_id,
            record.previous_value,
            record.new_value,
            record.timestamp,
            record.result.value,
            record.correlation_id,
        )
        if _fnv1a(payload) != record.integrity_hash:
            return False
        previous_hash = record.integrity_hash
    return True


async def enforce_retention(session: AsyncSession, retention_days: int) -> int:
    cutoff = utc_now() - timedelta(days=retention_days)
    state = await _anchor(session)
    expired = (
        await session.scalars(
            select(AuditRecord)
            .where(AuditRecord.timestamp < cutoff)
            .order_by(AuditRecord.id.asc())
        )
    ).all()
    if not expired:
        return 0
    state.anchor = expired[-1].integrity_hash
    for record in expired:
        await session.delete(record)
    return len(expired)
