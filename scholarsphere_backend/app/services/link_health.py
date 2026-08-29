"""Reachability check for a stored application/source URL.

Deliberately answers only "is this URL currently reachable", not "is this
still the correct application page" - confirming the destination actually
matches the opportunity is the verification officer's job
(VerificationReview.application_link_checked), not something this
periodic, unattended check can safely judge on its own.
"""

from __future__ import annotations

import logging

from app.core.http_client import ExternalAPIError, get_html

logger = logging.getLogger(__name__)


async def check_link_reachable(url: str) -> bool:
    try:
        await get_html(url)
        return True
    except ExternalAPIError as exc:
        logger.info(
            "link_health_check_failed status_code=%s",
            exc.status_code,
        )
        return False
