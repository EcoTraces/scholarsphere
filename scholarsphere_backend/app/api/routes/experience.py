from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES, require_roles
from app.db.session import get_db
from app.models.experience import ExperiencePreferences, TranslationEntry
from app.schemas.experience import (
    ExperiencePreferencesRead,
    SavePreferencesRequest,
    SaveTranslationRequest,
    TranslationRead,
    language_from_wire,
)
from app.services.parsing import utc_now

router = APIRouter(prefix="/experience", tags=["experience"])

any_authenticated = Depends(get_current_user)
# saveTranslation has no current UI caller (localization content management
# is an ops/content concern, not applicant self-service) - gated to staff,
# matching the pattern used for other no-current-caller interface methods
# elsewhere in this backend.
staff_access = Depends(require_roles(*STAFF_ROLES))


@router.get("/preferences", response_model=ExperiencePreferencesRead)
async def get_preferences(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ExperiencePreferencesRead:
    preferences = await session.get(ExperiencePreferences, user.uid)
    if preferences is None:
        # ExperiencePreferences' SQLAlchemy column defaults only apply at
        # flush/insert time, not on direct construction, so build the
        # default response explicitly rather than instantiating a
        # transient, never-flushed model row.
        return ExperiencePreferencesRead(
            language="english",
            timezone="UTC",
            currency_code="USD",
            country_code="US",
            text_scale=1.0,
            high_contrast=False,
            screen_reader_optimized=False,
            keyboard_navigation=True,
            low_bandwidth_mode=False,
            compress_images=True,
            data_saving=False,
            cache_saved_opportunities=True,
        )
    return ExperiencePreferencesRead.model_validate(preferences)


@router.put("/preferences", response_model=ExperiencePreferencesRead)
async def save_preferences(
    payload: SavePreferencesRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ExperiencePreferencesRead:
    async with session.begin():
        preferences = await session.get(ExperiencePreferences, user.uid)
        language = language_from_wire(payload.language)
        if preferences is None:
            preferences = ExperiencePreferences(user_id=user.uid)
            session.add(preferences)
        preferences.language = language
        preferences.timezone = payload.timezone
        preferences.currency_code = payload.currency_code
        preferences.country_code = payload.country_code
        preferences.text_scale = payload.text_scale
        preferences.high_contrast = payload.high_contrast
        preferences.screen_reader_optimized = payload.screen_reader_optimized
        preferences.keyboard_navigation = payload.keyboard_navigation
        preferences.low_bandwidth_mode = payload.low_bandwidth_mode
        preferences.compress_images = payload.compress_images
        preferences.data_saving = payload.data_saving
        preferences.cache_saved_opportunities = payload.cache_saved_opportunities
        preferences.updated_at = utc_now()
        await session.flush()
        await session.refresh(preferences)
        return ExperiencePreferencesRead.model_validate(preferences)


@router.put("/translations/{language}/{key}", response_model=TranslationRead)
async def save_translation(
    language: str,
    key: str,
    payload: SaveTranslationRequest,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TranslationRead:
    parsed_language = language_from_wire(language)
    async with session.begin():
        entry = await session.get(TranslationEntry, (parsed_language, key))
        if entry is None:
            entry = TranslationEntry(
                language=parsed_language,
                key=key,
                value=payload.value,
                updated_at=utc_now(),
                updated_by=user.uid,
            )
            session.add(entry)
        else:
            entry.value = payload.value
            entry.updated_at = utc_now()
            entry.updated_by = user.uid
        await session.flush()
        return TranslationRead(value=entry.value)


@router.get("/translations/{language}/{key}", response_model=TranslationRead)
async def translate(
    language: str,
    key: str,
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
    fallback: Annotated[str | None, Query()] = None,
) -> TranslationRead:
    parsed_language = language_from_wire(language)
    entry = await session.get(TranslationEntry, (parsed_language, key))
    if entry is not None:
        return TranslationRead(value=entry.value)
    return TranslationRead(value=fallback if fallback is not None else key)
