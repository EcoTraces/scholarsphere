"""Read-only: how many live opportunity records come from a direct
university source (OpportunitySource.source_type == 'university'),
broken down by verification/publication status. One-off, deleted after
use - see the equivalent pending-queue diagnostic in git history for
the same pattern.
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

from sqlalchemy import func, select  # noqa: E402

from app.db.session import AsyncSessionFactory  # noqa: E402
from app.models.external_opportunity import (  # noqa: E402
    ExternalOpportunity,
    OpportunitySource,
    PublicationStatus,
    VerificationStatus,
)


async def main() -> None:
    async with AsyncSessionFactory() as session:
        total_sources = await session.scalar(
            select(func.count(OpportunitySource.id)).where(
                OpportunitySource.source_type == "university"
            )
        )
        total_opportunities = await session.scalar(
            select(func.count(ExternalOpportunity.id))
            .join(OpportunitySource, OpportunitySource.id == ExternalOpportunity.source_id)
            .where(OpportunitySource.source_type == "university")
        )
        by_verification = (
            await session.execute(
                select(
                    ExternalOpportunity.verification_status,
                    func.count(ExternalOpportunity.id),
                )
                .join(OpportunitySource, OpportunitySource.id == ExternalOpportunity.source_id)
                .where(OpportunitySource.source_type == "university")
                .group_by(ExternalOpportunity.verification_status)
            )
        ).all()
        published = await session.scalar(
            select(func.count(ExternalOpportunity.id))
            .join(OpportunitySource, OpportunitySource.id == ExternalOpportunity.source_id)
            .where(
                OpportunitySource.source_type == "university",
                ExternalOpportunity.verification_status == VerificationStatus.verified,
                ExternalOpportunity.publication_status == PublicationStatus.published,
            )
        )
        by_source = (
            await session.execute(
                select(
                    OpportunitySource.source_name,
                    func.count(ExternalOpportunity.id),
                )
                .join(OpportunitySource, OpportunitySource.id == ExternalOpportunity.source_id)
                .where(OpportunitySource.source_type == "university")
                .group_by(OpportunitySource.source_name)
                .order_by(func.count(ExternalOpportunity.id).desc())
            )
        ).all()

    print(f"university-type sources registered: {total_sources}")
    print(f"total opportunity records from those sources: {total_opportunities}")
    print(f"live/published (verified + published): {published}")
    print("by verification_status:")
    for status, count in by_verification:
        print(f"  {status.value}: {count}")
    print(f"\nsources that have produced at least 1 record ({len(by_source)}):")
    for name, count in by_source:
        print(f"  {count:3d}  {name}")


if __name__ == "__main__":
    asyncio.run(main())
