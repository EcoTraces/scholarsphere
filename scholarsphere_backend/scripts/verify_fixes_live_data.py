"""Read-only: confirm the exact data the funding-type and application-
link fixes rely on, for the 3 currently verified+published university
opportunities. One-off, deleted after use.
"""

from __future__ import annotations

import asyncio
import os
import sys

if not os.environ.get("DATABASE_URL"):
    print("DATABASE_URL is not set.", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("APP_ENV", "development")

from sqlalchemy import select  # noqa: E402

from app.db.session import AsyncSessionFactory  # noqa: E402
from app.models.external_opportunity import (  # noqa: E402
    ExternalOpportunity,
    PublicationStatus,
    VerificationStatus,
)


async def main() -> None:
    async with AsyncSessionFactory() as session:
        rows = (
            await session.execute(
                select(
                    ExternalOpportunity.title,
                    ExternalOpportunity.funding_type,
                    ExternalOpportunity.official_source_url,
                    ExternalOpportunity.official_application_url,
                ).where(
                    ExternalOpportunity.verification_status == VerificationStatus.verified,
                    ExternalOpportunity.publication_status == PublicationStatus.published,
                )
            )
        ).all()

    for title, funding_type, source_url, application_url in rows:
        same = source_url == application_url
        print(f"- {title}")
        print(f"  funding_type: {funding_type!r}")
        print(f"  official_source_url:      {source_url}")
        print(f"  official_application_url: {application_url}")
        print(f"  urls identical: {same}")


if __name__ == "__main__":
    asyncio.run(main())
