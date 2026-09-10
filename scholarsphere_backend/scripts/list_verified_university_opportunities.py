"""Read-only: list the specific opportunity records from a direct
university source (OpportunitySource.source_type == 'university') that
are verified + published. Answers a direct follow-up to the earlier
university-opportunity count. One-off, deleted after use.
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
    OpportunitySource,
    PublicationStatus,
    VerificationStatus,
)


async def main() -> None:
    async with AsyncSessionFactory() as session:
        rows = (
            await session.execute(
                select(
                    ExternalOpportunity.title,
                    OpportunitySource.source_name,
                    ExternalOpportunity.country,
                    ExternalOpportunity.deadline,
                    ExternalOpportunity.official_source_url,
                )
                .join(OpportunitySource, OpportunitySource.id == ExternalOpportunity.source_id)
                .where(
                    OpportunitySource.source_type == "university",
                    ExternalOpportunity.verification_status == VerificationStatus.verified,
                    ExternalOpportunity.publication_status == PublicationStatus.published,
                )
            )
        ).all()

    print(f"{len(rows)} verified+published university opportunities:")
    for title, source_name, country, deadline, url in rows:
        print(f"- {title}")
        print(f"  source: {source_name} | country: {country} | deadline: {deadline}")
        print(f"  {url}")


if __name__ == "__main__":
    asyncio.run(main())
