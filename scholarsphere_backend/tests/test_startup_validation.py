from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.main import ensure_firebase_ready_in_production


def test_production_refuses_nonexistent_firebase_credentials_file(tmp_path) -> None:
    missing = tmp_path / "does-not-exist.json"
    with pytest.raises(ValidationError, match="FIREBASE_CREDENTIALS_PATH"):
        Settings(
            app_env="production",
            database_url="postgresql+asyncpg://scholarsphere:a-real-password@real-db-host:5432/scholarsphere",
            redis_url="redis://real-redis-host:6379/0",
            firebase_credentials_path=missing,
        )


def test_production_accepts_a_real_firebase_credentials_file(tmp_path) -> None:
    real = tmp_path / "service-account.json"
    real.write_text("{}", encoding="utf-8")
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://scholarsphere:a-real-password@real-db-host:5432/scholarsphere",
        redis_url="redis://real-redis-host:6379/0",
        firebase_credentials_path=real,
    )
    assert settings.firebase_credentials_path == real


def test_production_allows_no_credentials_path_for_application_default_credentials() -> None:
    """No FIREBASE_CREDENTIALS_PATH is valid in production when the
    deployment relies on Application Default Credentials instead (e.g. a
    service account attached to the GCP compute environment) - only an
    explicitly-set-but-missing path is refused."""
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://scholarsphere:a-real-password@real-db-host:5432/scholarsphere",
        redis_url="redis://real-redis-host:6379/0",
    )
    assert settings.firebase_credentials_path is None


def test_ensure_firebase_ready_is_a_noop_outside_production() -> None:
    ensure_firebase_ready_in_production(SimpleNamespace(app_env="development"))
    ensure_firebase_ready_in_production(SimpleNamespace(app_env="test"))


def test_ensure_firebase_ready_raises_actionable_error_on_init_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.main as main_module

    failing_init = MagicMock(side_effect=ValueError("bad credential"))
    monkeypatch.setattr(main_module, "initialize_firebase", failing_init)

    with pytest.raises(RuntimeError, match="FIREBASE_CREDENTIALS_PATH"):
        ensure_firebase_ready_in_production(SimpleNamespace(app_env="production"))
    failing_init.assert_called_once()


def test_ensure_firebase_ready_passes_when_init_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.main as main_module

    succeeding_init = MagicMock(return_value=object())
    monkeypatch.setattr(main_module, "initialize_firebase", succeeding_init)

    ensure_firebase_ready_in_production(SimpleNamespace(app_env="production"))
    succeeding_init.assert_called_once()
