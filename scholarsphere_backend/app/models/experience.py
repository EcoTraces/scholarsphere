import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SupportedLanguage(str, enum.Enum):
    english = "english"
    french = "french"
    spanish = "spanish"
    arabic = "arabic"


class ExperiencePreferences(Base):
    __tablename__ = "experience_preferences"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    language: Mapped[SupportedLanguage] = mapped_column(
        Enum(SupportedLanguage, native_enum=False),
        default=SupportedLanguage.english,
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), default="US", nullable=False)
    text_scale: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    high_contrast: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    screen_reader_optimized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    keyboard_navigation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    low_bandwidth_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    compress_images: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    data_saving: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cache_saved_opportunities: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TranslationEntry(Base):
    __tablename__ = "translation_entries"

    language: Mapped[SupportedLanguage] = mapped_column(
        Enum(SupportedLanguage, native_enum=False), primary_key=True
    )
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)
