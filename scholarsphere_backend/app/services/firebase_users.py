"""Enumerate real Firebase users holding a reverification-eligible role.

This backend has no local user table - identity lives entirely in Firebase
(see Database.md SS1) - and the Firebase Admin SDK does not expose a
server-side "query users by custom claim" call; custom claims are opaque
JSON blobs attached to a user record, not an indexed/queryable field. The
officially supported pattern (confirmed against the installed
`firebase-admin` SDK's API surface) is to paginate every user via
`auth.list_users()` and filter client-side.

This is the real roster source for reverification reminders
(app/tasks/opportunity_sync.py), replacing the audit-log-activity
heuristic as the primary source so that officers who have never made a
verification decision still receive reminders. The audit-log heuristic
remains as an explicit, logged fallback if Firebase enumeration itself
fails (e.g. no credentials configured in this environment) - fail
*safely*, not fail to zero recipients.
"""

from __future__ import annotations

import logging

import firebase_admin
from firebase_admin import auth as firebase_auth

from app.core.auth import ROLE_ALIASES, initialize_firebase

logger = logging.getLogger(__name__)

# Mirrors preview_access/import_access in
# app/api/routes/external_opportunities.py: the roles that can act on the
# verification queue, and therefore the roles reverification reminders
# should reach.
REVERIFICATION_ROLES = frozenset(
    {"verificationOfficer", "administrator", "superAdministrator"}
)


class FirebaseRosterError(Exception):
    """Raised when the Firebase user roster could not be retrieved at all.

    Distinguished from an empty-but-successful roster (0 matching users is
    a valid, real answer) so callers can tell "we asked Firebase and no one
    currently holds this role" apart from "we could not ask Firebase".
    """


def _normalized_role(claims: dict[str, object]) -> str | None:
    raw_role = claims.get("role")
    if not isinstance(raw_role, str) or not raw_role:
        return None
    return ROLE_ALIASES.get(raw_role, raw_role)


def list_reverification_recipient_uids(
    *, app: firebase_admin.App | None = None, page_size: int = 1000
) -> list[str]:
    """Every enabled user holding a REVERIFICATION_ROLES custom claim.

    Deduplicated, order-preserving. Disabled Firebase accounts are
    excluded - a disabled account cannot sign in to act on a reminder
    regardless of its claims, so notifying it would be pointless at best.

    Raises FirebaseRosterError (never a raw firebase_admin/gRPC exception)
    on any failure, so callers get one exception type to handle uniformly.
    """
    resolved_app = app or initialize_firebase()
    uids: list[str] = []
    seen: set[str] = set()
    scanned = 0
    try:
        page = firebase_auth.list_users(app=resolved_app, max_results=page_size)
        while page is not None:
            for user in page.users:
                scanned += 1
                if user.disabled:
                    continue
                role = _normalized_role(user.custom_claims or {})
                if role in REVERIFICATION_ROLES and user.uid not in seen:
                    seen.add(user.uid)
                    uids.append(user.uid)
            page = page.get_next_page()
    except Exception as error:  # noqa: BLE001 - deliberately broad, see docstring
        # Never log the exception body verbatim - firebase_admin exceptions
        # can wrap transport details; the type name is enough to diagnose
        # from server-side logs without risking sensitive data exposure.
        logger.warning(
            "firebase_roster_enumeration_failed error_type=%s scanned_before_failure=%s",
            type(error).__name__,
            scanned,
        )
        raise FirebaseRosterError(
            f"Could not enumerate Firebase users: {type(error).__name__}"
        ) from error
    logger.info(
        "firebase_roster_enumerated scanned=%s matched=%s", scanned, len(uids)
    )
    return uids
