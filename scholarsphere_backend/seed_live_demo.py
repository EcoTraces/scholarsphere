"""One-off local demo seeding: pulls REAL live records from Grants.gov (the
only one of our three official sources reachable without a registered API
key from this environment) through the exact production pipeline -
import -> verify -> publish - against the throwaway local SQLite database
used for this local demo run only. Not for production use.

Verification/publication decisions here are made by this script acting as
a stand-in reviewer for local-demo purposes only (actor id
"demo-agent-local-seed"), using the same checklist and RBAC-gated endpoints
production traffic uses - nothing is written directly to the database
bypassing those checks. This is disclosed in the audit trail and should not
be mistaken for an actual ScholarSphere verification officer's review.
"""

import asyncio
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///dev_smoke.db")

from pydantic import ValidationError  # noqa: E402

from app.core.config import get_settings  # noqa: E402

try:
    _settings = get_settings()
except ValidationError as error:
    # Settings itself now refuses insecure placeholder infrastructure
    # credentials under APP_ENV=production (see
    # Settings.reject_placeholder_infrastructure_credentials_in_production)
    # before this script's own sqlite-only check below ever runs.
    sys.exit(
        "seed_live_demo.py refuses to run: app configuration rejected the "
        f"current environment ({error}). This script must only ever run "
        "against the throwaway local dev_smoke.db in a non-production "
        "environment."
    )
if _settings.app_env == "production" or "sqlite" not in _settings.database_url:
    sys.exit(
        "seed_live_demo.py refuses to run: APP_ENV is 'production' or "
        "DATABASE_URL does not point at a local sqlite file "
        f"(app_env={_settings.app_env!r}, database_url does not contain "
        "'sqlite'). This script auto-approves and publishes records; it "
        "must only ever run against the throwaway local dev_smoke.db."
    )

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.auth import AuthenticatedUser, get_current_user  # noqa: E402
from app.db.session import AsyncSessionFactory, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.grants_gov import GrantsGovSource  # noqa: E402
from app.services.opportunity_import import import_opportunities  # noqa: E402


def user(role: str) -> AuthenticatedUser:
    return AuthenticatedUser(
        uid="demo-agent-local-seed",
        email="demo-agent@local.invalid",
        email_verified=True,
        role=role,
        permissions=frozenset(),
    )


async def main() -> None:
    print("Fetching live records from Grants.gov...")
    records = await GrantsGovSource().collect_for_import(page=1, page_size=15)
    print(f"Fetched {len(records)} live records from Grants.gov.")

    async with AsyncSessionFactory() as session:
        statistics = await import_opportunities(
            session, records, source_code="grants_gov", actor_id="demo-agent-local-seed"
        )
    print(
        f"Imported: created={statistics.records_created} "
        f"updated={statistics.records_updated} skipped={statistics.records_skipped} "
        f"failed={statistics.records_failed}"
    )

    async def current_user_admin():
        return user("administrator")

    async def database():
        async with AsyncSessionFactory() as session:
            yield session

    app.dependency_overrides[get_current_user] = current_user_admin
    app.dependency_overrides[get_db] = database

    published = 0
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://local") as client:
        pending = await client.get(
            "/api/v1/external-opportunities/pending-verification",
            params={"source": "grants-gov", "page_size": 50},
        )
        items = pending.json()["items"]
        print(f"{len(items)} record(s) pending verification.")
        for item in items:
            opportunity_id = item["id"]
            verify = await client.post(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}/verification",
                json={
                    "decision": "approved",
                    "notes": (
                        "Collected live from the official Grants.gov Search2 API and "
                        "verified for local ScholarSphere demo purposes only "
                        "(automated stand-in reviewer, not a human verification officer)."
                    ),
                    "source_checked": True,
                    "application_link_checked": True,
                    "deadline_checked": True,
                    "duplicate_checked": True,
                },
            )
            if verify.status_code != 200:
                print(f"  verify failed for {item['title']}: {verify.status_code} {verify.text}")
                continue
            publish = await client.post(
                f"/api/v1/external-opportunities/opportunities/{opportunity_id}/publication",
                json={"published": True},
            )
            if publish.status_code == 200:
                published += 1
            else:
                print(f"  publish failed for {item['title']}: {publish.status_code} {publish.text}")

    app.dependency_overrides.clear()
    print(f"Published {published} record(s) to the public API.")


if __name__ == "__main__":
    asyncio.run(main())
