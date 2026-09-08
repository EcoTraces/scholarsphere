"""Run the real collect+import pipeline for every registered opportunity
source directly against the production database.

Exists because Render's free tier (see render.yaml and
docs/DEPLOYMENT_FREE_TIER.md) cannot run a Celery worker/beat process, so
none of the 109 scheduled source-sync tasks normally run in production at
all. This script is invoked on a schedule by
.github/workflows/sync-opportunities.yml, whose GitHub-hosted runner has
the outbound network access this needs (unlike Render's own environment,
which cannot reach every source site either).

Deliberately calls _run_source_sync directly - the exact coroutine the
real Celery tasks call - so this is the same code path production itself
uses, not a reimplementation.

Import only. Never verifies or publishes anything - that stays a real
verification officer's decision in the app, same as if a worker had run
this. Safe to re-run on a schedule: import_opportunities() is upsert-based
per source.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid

if not os.environ.get("DATABASE_URL"):
    print("DATABASE_URL is not set.", file=sys.stderr)
    sys.exit(1)

os.environ.setdefault("APP_ENV", "development")  # avoid the production-only strict validator

from app.tasks.opportunity_sync import SOURCE_TASK_NAMES, _run_source_sync  # noqa: E402

CONCURRENCY = 8
TIMEOUT_SECONDS = 180


async def run_one(source_code: str, sem: asyncio.Semaphore) -> tuple[str, str]:
    async with sem:
        task_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        try:
            result = await asyncio.wait_for(
                _run_source_sync(
                    source_code,
                    task_id=task_id,
                    correlation_id=correlation_id,
                    triggered_by="github-actions-sync",
                ),
                timeout=TIMEOUT_SECONDS,
            )
            return source_code, (
                f"OK created={result.get('records_created')} "
                f"updated={result.get('records_updated')} "
                f"skipped={result.get('records_skipped')} "
                f"failed={result.get('records_failed')} "
                f"status={result.get('status')}"
            )
        except Exception as error:  # noqa: BLE001 - report every failure, keep going
            return source_code, f"FAILED {type(error).__name__}: {error}"


async def main() -> None:
    sem = asyncio.Semaphore(CONCURRENCY)
    started = time.monotonic()
    tasks = [run_one(code, sem) for code in SOURCE_TASK_NAMES]
    results = await asyncio.gather(*tasks)
    elapsed = time.monotonic() - started

    ok = [r for r in results if r[1].startswith("OK")]
    failed = [r for r in results if not r[1].startswith("OK")]
    total_created = sum(int(msg.split("created=")[1].split()[0]) for _, msg in ok)

    print(f"\n=== {len(results)} sources processed in {elapsed:.1f}s ===")
    print(f"Succeeded: {len(ok)}  Failed: {len(failed)}")
    print(f"Total new opportunities created: {total_created}\n")
    for code, msg in sorted(results):
        print(f"{code}: {msg}")

    if failed:
        print(f"\n{len(failed)} source(s) failed:", file=sys.stderr)
        for code, msg in sorted(failed):
            print(f"  {code}: {msg}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
