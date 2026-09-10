"""Read-only diagnostic: why does the Verification Officer dashboard show
a large "Pending Verification" count while the actual queue screen says
"The verification queue is clear."?

Compares the raw SQL an officer's dashboard summary uses (just
verification_status == pending) against the SQL the queue listing and the
Flutter verification-queue screen use (verification_status == pending AND
publication_status == unpublished, AND a non-null deadline once mapped to
the Opportunity domain type client-side). Prints counts only - never
writes anything.
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
    PublicationStatus,
    VerificationStatus,
)


async def main() -> None:
    async with AsyncSessionFactory() as session:
        pending_total = await session.scalar(
            select(func.count(ExternalOpportunity.id)).where(
                ExternalOpportunity.verification_status == VerificationStatus.pending
            )
        )
        pending_unpublished = await session.scalar(
            select(func.count(ExternalOpportunity.id)).where(
                ExternalOpportunity.verification_status == VerificationStatus.pending,
                ExternalOpportunity.publication_status == PublicationStatus.unpublished,
            )
        )
        pending_by_pubstatus = (
            await session.execute(
                select(
                    ExternalOpportunity.publication_status,
                    func.count(ExternalOpportunity.id),
                )
                .where(ExternalOpportunity.verification_status == VerificationStatus.pending)
                .group_by(ExternalOpportunity.publication_status)
            )
        ).all()
        pending_unpublished_no_deadline = await session.scalar(
            select(func.count(ExternalOpportunity.id)).where(
                ExternalOpportunity.verification_status == VerificationStatus.pending,
                ExternalOpportunity.publication_status == PublicationStatus.unpublished,
                ExternalOpportunity.deadline.is_(None),
            )
        )
        pending_unpublished_no_opening = await session.scalar(
            select(func.count(ExternalOpportunity.id)).where(
                ExternalOpportunity.verification_status == VerificationStatus.pending,
                ExternalOpportunity.publication_status == PublicationStatus.unpublished,
                ExternalOpportunity.opening_date.is_(None),
                ExternalOpportunity.collected_at.is_(None),
            )
        )
        sample = (
            await session.execute(
                select(
                    ExternalOpportunity.id,
                    ExternalOpportunity.title,
                    ExternalOpportunity.verification_status,
                    ExternalOpportunity.publication_status,
                    ExternalOpportunity.deadline,
                    ExternalOpportunity.opening_date,
                    ExternalOpportunity.collected_at,
                )
                .where(ExternalOpportunity.verification_status == VerificationStatus.pending)
                .limit(10)
            )
        ).all()

    print(f"pending (verification_status=pending): {pending_total}")
    print(f"pending AND publication_status=unpublished: {pending_unpublished}")
    print("pending, grouped by publication_status:")
    for status, count in pending_by_pubstatus:
        print(f"  {status.value}: {count}")
    print(f"pending+unpublished with deadline IS NULL: {pending_unpublished_no_deadline}")
    print(
        "pending+unpublished with opening_date AND collected_at both NULL: "
        f"{pending_unpublished_no_opening}"
    )
    print("\nFirst 10 pending rows (any publication_status):")
    for row in sample:
        print(
            f"  id={row.id} title={row.title!r} "
            f"pub_status={row.publication_status.value} "
            f"deadline={row.deadline} opening_date={row.opening_date} "
            f"collected_at={row.collected_at}"
        )


if __name__ == "__main__":
    asyncio.run(main())
