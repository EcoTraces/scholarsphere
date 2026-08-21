from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditAction, AuditResult
from app.models.system_configuration import PlatformConfiguration
from app.schemas.system_configuration import (
    DEFAULT_FEATURE_FLAGS,
    PlatformConfigurationRead,
    RollbackRequest,
    SaveConfigurationRequest,
)
from app.services.audit_log import append_audit_record
from app.services.parsing import utc_now

router = APIRouter(prefix="/system-configuration", tags=["system configuration"])

# Matches DemoSystemConfigurationRepository._authorize exactly.
config_access = Depends(require_roles("administrator", "securityAdministrator", "superAdministrator"))


async def _current(session: AsyncSession) -> PlatformConfiguration:
    config = await session.scalar(
        select(PlatformConfiguration).order_by(PlatformConfiguration.version.desc()).limit(1)
    )
    if config is None:
        config = PlatformConfiguration(
            version=1,
            platform_name="ScholarSphere",
            logo_location="assets/branding/logo.png",
            brand_primary_color="#007C72",
            email_sender_name="ScholarSphere",
            email_sender_address="no-reply@scholarsphere.example",
            verification_expiration_days=90,
            supported_countries=["Global"],
            supported_languages=["en"],
            opportunity_categories=["scholarship", "fellowship", "internship"],
            document_types=["passport", "transcript", "curriculum_vitae"],
            maximum_file_size_bytes=10 * 1024 * 1024,
            applicant_registration_enabled=True,
            provider_registration_enabled=True,
            maintenance_mode=False,
            feature_flags=dict(DEFAULT_FEATURE_FLAGS),
            environment={"name": "development", "apiVersion": "v1"},
            security_policy={"minimumPasswordLength": 12, "mfaForAdministrators": True},
            recommendation_settings={"diversityEnabled": True, "limit": 20},
            fraud_rule_settings={"automaticHideScore": 90},
            integration_settings={"sandboxEnabled": True},
            notification_settings={"dailyLimit": 10},
            updated_at=None,
            updated_by="system",
            change_reason="Initial configuration",
        )
        session.add(config)
        await session.flush()
    return config


def _check_cross_field_rules(payload: SaveConfigurationRequest) -> None:
    if payload.feature_flags.get("providerSelfPublication") and not payload.security_policy.get(
        "mfaForAdministrators"
    ):
        raise HTTPException(
            status_code=409,
            detail="Provider self-publication requires the stronger security policy.",
        )


@router.get("/current", response_model=PlatformConfigurationRead)
async def current_configuration(
    _: Annotated[AuthenticatedUser, config_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformConfigurationRead:
    return PlatformConfigurationRead.model_validate(await _current(session))


@router.get("/history", response_model=list[PlatformConfigurationRead])
async def configuration_history(
    _: Annotated[AuthenticatedUser, config_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PlatformConfigurationRead]:
    await _current(session)
    rows = await session.scalars(
        select(PlatformConfiguration).order_by(PlatformConfiguration.version.desc())
    )
    return [PlatformConfigurationRead.model_validate(row) for row in rows.all()]


@router.put("", response_model=PlatformConfigurationRead)
async def update_configuration(
    payload: SaveConfigurationRequest,
    user: Annotated[AuthenticatedUser, config_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformConfigurationRead:
    _check_cross_field_rules(payload)
    async with session.begin():
        previous = await _current(session)
        now = utc_now()
        updated = PlatformConfiguration(
            version=previous.version + 1,
            platform_name=payload.platform_name,
            logo_location=payload.logo_location,
            brand_primary_color=payload.brand_primary_color,
            email_sender_name=payload.email_sender_name,
            email_sender_address=payload.email_sender_address,
            verification_expiration_days=payload.verification_expiration_days,
            supported_countries=payload.supported_countries,
            supported_languages=payload.supported_languages,
            opportunity_categories=payload.opportunity_categories,
            document_types=payload.document_types,
            maximum_file_size_bytes=payload.maximum_file_size_bytes,
            applicant_registration_enabled=payload.applicant_registration_enabled,
            provider_registration_enabled=payload.provider_registration_enabled,
            maintenance_mode=payload.maintenance_mode,
            feature_flags=payload.feature_flags,
            environment=payload.environment,
            security_policy=payload.security_policy,
            recommendation_settings=payload.recommendation_settings,
            fraud_rule_settings=payload.fraud_rule_settings,
            integration_settings=payload.integration_settings,
            notification_settings=payload.notification_settings,
            updated_at=now,
            updated_by=user.uid,
            change_reason=payload.reason,
        )
        session.add(updated)
        await append_audit_record(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action=AuditAction.administrativeAction,
            entity_type="platform_configuration",
            entity_id="global",
            previous_value=f"version={previous.version}",
            new_value=f"version={updated.version}",
            result=AuditResult.success,
            correlation_id=f"config-{updated.version}",
        )
        await session.flush()
        return PlatformConfigurationRead.model_validate(updated)


@router.post("/rollback", response_model=PlatformConfigurationRead)
async def rollback_configuration(
    payload: RollbackRequest,
    user: Annotated[AuthenticatedUser, config_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformConfigurationRead:
    target = await session.get(PlatformConfiguration, payload.target_version)
    if target is None:
        raise HTTPException(status_code=404, detail="Configuration version was not found.")
    await session.commit()
    restore = SaveConfigurationRequest(
        platform_name=target.platform_name,
        logo_location=target.logo_location,
        brand_primary_color=target.brand_primary_color,
        email_sender_name=target.email_sender_name,
        email_sender_address=target.email_sender_address,
        verification_expiration_days=target.verification_expiration_days,
        supported_countries=target.supported_countries,
        supported_languages=target.supported_languages,
        opportunity_categories=target.opportunity_categories,
        document_types=target.document_types,
        maximum_file_size_bytes=target.maximum_file_size_bytes,
        applicant_registration_enabled=target.applicant_registration_enabled,
        provider_registration_enabled=target.provider_registration_enabled,
        maintenance_mode=target.maintenance_mode,
        feature_flags=target.feature_flags,
        environment=target.environment,
        security_policy=target.security_policy,
        recommendation_settings=target.recommendation_settings,
        fraud_rule_settings=target.fraud_rule_settings,
        integration_settings=target.integration_settings,
        notification_settings=target.notification_settings,
        reason=f"Rollback: {payload.reason}",
    )
    return await update_configuration(restore, user, session)
