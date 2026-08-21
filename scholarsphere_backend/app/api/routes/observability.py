import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.observability import (
    AlertRule,
    ApplicationLog,
    HealthStatus,
    IncidentStatus,
    LogLevel,
    MetricPoint,
    OperationalIncident,
    TraceSpan,
)
from app.schemas.observability import (
    AlertRuleRead,
    ApplicationLogRead,
    OperationalIncidentRead,
    PerformanceReportRead,
    RecordLogRequest,
    RecordMetricRequest,
    RecordTraceRequest,
    SaveAlertRuleRequest,
    ServiceHealthRead,
)
from app.services.parsing import utc_now

router = APIRouter(prefix="/observability", tags=["observability"])

# DemoObservabilityRepository enforces no role check at all (a single
# trusted demo process can safely accept telemetry from anywhere). That
# trust boundary doesn't survive becoming a shared multi-tenant backend -
# an unauthenticated write here would let any caller pollute the ops log
# stream or spuriously trigger incidents, so every route is staff-gated
# here instead, consistent with the rest of the operations cluster.
observability_access = Depends(
    require_roles("administrator", "securityAdministrator", "superAdministrator")
)

_LOG_LEVEL_ORDER = {level: index for index, level in enumerate(LogLevel)}


@router.post("/logs", status_code=204)
async def record_log(
    payload: RecordLogRequest,
    _: Annotated[AuthenticatedUser, observability_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        session.add(
            ApplicationLog(
                level=payload.level,
                service=payload.service,
                message=payload.message,
                timestamp=payload.timestamp,
                correlation_id=payload.correlation_id,
                context=payload.context,
            )
        )


@router.get("/logs", response_model=list[ApplicationLogRead])
async def search_logs(
    _: Annotated[AuthenticatedUser, observability_access],
    session: Annotated[AsyncSession, Depends(get_db)],
    minimum_level: Annotated[LogLevel | None, Query()] = None,
    service: Annotated[str | None, Query()] = None,
    query: Annotated[str | None, Query()] = None,
) -> list[ApplicationLogRead]:
    rows = (await session.scalars(select(ApplicationLog))).all()
    normalized = query.lower() if query else None
    filtered = [
        row
        for row in rows
        if (minimum_level is None or _LOG_LEVEL_ORDER[row.level] >= _LOG_LEVEL_ORDER[minimum_level])
        and (service is None or row.service == service)
        and (
            normalized is None
            or normalized in row.message.lower()
            or normalized in row.correlation_id.lower()
        )
    ]
    return [ApplicationLogRead.model_validate(row) for row in filtered]


@router.post("/metrics", status_code=204)
async def record_metric(
    payload: RecordMetricRequest,
    _: Annotated[AuthenticatedUser, observability_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        session.add(
            MetricPoint(
                name=payload.name,
                value=payload.value,
                unit=payload.unit,
                timestamp=payload.timestamp,
                labels=payload.labels,
            )
        )
        rules = (
            await session.scalars(
                select(AlertRule).where(
                    AlertRule.enabled.is_(True), AlertRule.metric_name == payload.name
                )
            )
        ).all()
        now = utc_now()
        for rule in rules:
            triggered = (
                payload.value > rule.threshold
                if rule.comparison == "greaterThan"
                else payload.value < rule.threshold
            )
            if not triggered:
                continue
            session.add(
                OperationalIncident(
                    id=f"incident-{uuid.uuid4().hex}",
                    title=f"{payload.name} crossed {rule.threshold}",
                    severity=rule.severity,
                    status=IncidentStatus.open,
                    created_at=now,
                    escalation_target=rule.escalation_target,
                    notes=[f"Observed value: {payload.value} {payload.unit}"],
                )
            )


@router.post("/traces", status_code=204)
async def record_trace(
    payload: RecordTraceRequest,
    _: Annotated[AuthenticatedUser, observability_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        existing = await session.get(TraceSpan, (payload.trace_id, payload.span_id))
        if existing is None:
            existing = TraceSpan(trace_id=payload.trace_id, span_id=payload.span_id)
            session.add(existing)
        existing.parent_span_id = payload.parent_span_id
        existing.operation = payload.operation
        existing.service = payload.service
        existing.started_at = payload.started_at
        existing.duration_seconds = payload.duration_seconds
        existing.successful = payload.successful


@router.get("/health", response_model=list[ServiceHealthRead])
async def health(
    _: Annotated[AuthenticatedUser, observability_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ServiceHealthRead]:
    """Reports real signals for the services this backend can actually
    observe (database connectivity, the API process itself). The demo's
    `registerHealthCheck` registers an arbitrary in-process Dart closure,
    which a Python backend has no way to execute - rather than fake that
    registry, this reports genuine health for what the server can see.
    """
    now = utc_now()
    started = datetime.now()
    try:
        await session.execute(text("SELECT 1"))
        database_status = HealthStatus.healthy
        details: dict[str, object] = {}
    except Exception as error:  # noqa: BLE001
        database_status = HealthStatus.unavailable
        details = {"error": str(error)}
    latency_ms = int((datetime.now() - started).total_seconds() * 1000)
    return [
        ServiceHealthRead(
            service="database",
            status=database_status,
            checked_at=now,
            latency_milliseconds=latency_ms,
            details=details,
        ),
        ServiceHealthRead(
            service="api",
            status=HealthStatus.healthy,
            checked_at=now,
            latency_milliseconds=0,
            details={},
        ),
    ]


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleRead)
async def save_alert_rule(
    rule_id: str,
    payload: SaveAlertRuleRequest,
    _: Annotated[AuthenticatedUser, observability_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AlertRuleRead:
    async with session.begin():
        rule = await session.get(AlertRule, rule_id)
        if rule is None:
            rule = AlertRule(id=rule_id)
            session.add(rule)
        rule.metric_name = payload.metric_name
        rule.threshold = payload.threshold
        rule.comparison = payload.comparison
        rule.severity = payload.severity
        rule.escalation_target = payload.escalation_target
        rule.enabled = payload.enabled
        await session.flush()
        return AlertRuleRead.model_validate(rule)


@router.get("/incidents", response_model=list[OperationalIncidentRead])
async def incidents(
    _: Annotated[AuthenticatedUser, observability_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[OperationalIncidentRead]:
    rows = await session.scalars(
        select(OperationalIncident).order_by(OperationalIncident.created_at.asc())
    )
    return [OperationalIncidentRead.model_validate(row) for row in rows.all()]


@router.get("/performance-report", response_model=PerformanceReportRead)
async def performance_report(
    _: Annotated[AuthenticatedUser, observability_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PerformanceReportRead:
    metrics = (await session.scalars(select(MetricPoint))).all()
    request_metrics = [metric for metric in metrics if metric.name == "request.duration_ms"]
    errors = [metric for metric in metrics if metric.name == "request.error"]
    latest: dict[str, float] = {}
    for metric in metrics:
        latest[metric.name] = metric.value
    return PerformanceReportRead(
        request_volume=len(request_metrics),
        error_rate=0 if not request_metrics else len(errors) / len(request_metrics),
        average_response_milliseconds=(
            0
            if not request_metrics
            else sum(metric.value for metric in request_metrics) / len(request_metrics)
        ),
        metrics=latest,
        generated_at=utc_now(),
    )


@router.post("/logs/enforce-retention", response_model=int)
async def enforce_log_retention(
    retention_seconds: Annotated[int, Query(ge=0)],
    _: Annotated[AuthenticatedUser, observability_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> int:
    async with session.begin():
        cutoff = utc_now() - timedelta(seconds=retention_seconds)
        expired = (
            await session.scalars(select(ApplicationLog).where(ApplicationLog.timestamp < cutoff))
        ).all()
        for row in expired:
            await session.delete(row)
        return len(expired)
