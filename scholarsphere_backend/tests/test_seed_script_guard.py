import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED_SCRIPT = REPO_ROOT / "seed_live_demo.py"


def _run_with_env(env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SEED_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_refuses_to_run_when_app_env_is_production(tmp_path) -> None:
    import os

    env = dict(os.environ)
    env["APP_ENV"] = "production"
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp_path / 'prod-looking.db'}"
    result = _run_with_env(env)
    assert result.returncode != 0
    assert "refuses to run" in result.stdout + result.stderr


def test_refuses_to_run_against_a_non_sqlite_database_url() -> None:
    import os

    env = dict(os.environ)
    env["APP_ENV"] = "development"
    env["DATABASE_URL"] = "postgresql+asyncpg://user:pass@prod-db.internal:5432/scholarsphere"
    result = _run_with_env(env)
    assert result.returncode != 0
    assert "refuses to run" in result.stdout + result.stderr
