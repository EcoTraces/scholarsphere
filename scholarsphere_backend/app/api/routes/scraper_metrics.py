"""Exposes the hybrid HTTP/browser-rendering scraper engine's in-process
counters (`app.services.scraper_metrics`) for the administration
dashboard. The spec's own example path was `GET /admin/scraper/metrics`;
adapted here to this project's existing flat, kebab-case router
convention (there is no `/admin` prefix namespace anywhere else in this
codebase - see e.g. `/source-registry`, `/system-configuration`) as
`GET /api/v1/scraper-metrics`.

Read-only: this only ever returns the current in-process snapshot (see
`ScraperMetrics.snapshot`'s own docstring for why it's in-memory and
resets on process restart, not a persisted time series). Staff-gated,
matching every other internal-operations endpoint in this cluster
(`app/api/routes/observability.py`, `app/api/routes/source_registry.py`).
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser
from app.core.rbac import require_roles
from app.services.scraper_metrics import get_metrics

router = APIRouter(prefix="/scraper-metrics", tags=["scraper-metrics"])

staff_access = Depends(
    require_roles("administrator", "securityAdministrator", "superAdministrator")
)


@router.get("", response_model=dict[str, int | float | None])
async def read_scraper_metrics(
    _: Annotated[AuthenticatedUser, staff_access],
) -> dict[str, int | float | None]:
    return get_metrics().snapshot()
