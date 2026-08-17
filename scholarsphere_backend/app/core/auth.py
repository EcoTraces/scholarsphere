import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Final

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)
ROLE_ALIASES = {
    "opportunity_provider": "opportunityProvider",
    "verification_officer": "verificationOfficer",
    "support_officer": "supportOfficer",
    "security_administrator": "securityAdministrator",
    "super_administrator": "superAdministrator",
}

ALL_PERMISSIONS: Final = frozenset(
    {
        "viewOpportunities",
        "manageOwnProfile",
        "manageOwnDocuments",
        "trackApplications",
        "submitOpportunity",
        "manageProviderOpportunities",
        "verifyOpportunity",
        "moderateContent",
        "supportUsers",
        "viewAdministration",
        "manageUsers",
        "manageSecurity",
        "suspendAccounts",
        "manageSecrets",
        "exportReports",
    }
)

# Mirrors lib/features/security/domain/access_control.dart's
# AccessControlPolicy exactly. Permissions are derived from role here
# rather than read from an independently-settable token claim: the
# Firebase Cloud Function that issues custom claims (functions/index.js)
# only ever sets `role`, never `permissions`, so trusting a separate claim
# would mean every permission check silently denies every
# non-superAdministrator user. Deriving permissions from role instead
# makes the two structurally impossible to drift out of sync.
ROLE_PERMISSIONS: Final[dict[str, frozenset[str]]] = {
    "applicant": frozenset(
        {
            "viewOpportunities",
            "manageOwnProfile",
            "manageOwnDocuments",
            "trackApplications",
        }
    ),
    "opportunityProvider": frozenset(
        {
            "viewOpportunities",
            "submitOpportunity",
            "manageProviderOpportunities",
        }
    ),
    "verificationOfficer": frozenset({"viewOpportunities", "verifyOpportunity"}),
    "moderator": frozenset({"viewOpportunities", "moderateContent"}),
    "supportOfficer": frozenset({"viewOpportunities", "supportUsers"}),
    "administrator": frozenset(
        {
            "viewOpportunities",
            "viewAdministration",
            "manageUsers",
            "exportReports",
        }
    ),
    "securityAdministrator": frozenset(
        {
            "viewAdministration",
            "manageSecurity",
            "suspendAccounts",
            "manageSecrets",
        }
    ),
    "superAdministrator": ALL_PERMISSIONS,
}


def permissions_for_role(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


@dataclass(frozen=True)
class AuthenticatedUser:
    uid: str
    email: str | None
    email_verified: bool
    role: str
    permissions: frozenset[str]


@lru_cache
def initialize_firebase() -> firebase_admin.App:
    settings = get_settings()
    if settings.firebase_credentials_path:
        credential = credentials.Certificate(str(settings.firebase_credentials_path))
        return firebase_admin.initialize_app(
            credential,
            {"projectId": settings.firebase_project_id},
        )
    return firebase_admin.initialize_app(
        options={"projectId": settings.firebase_project_id}
    )


async def get_current_user(
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        initialize_firebase()
        claims = auth.verify_id_token(
            token.credentials,
            check_revoked=settings.firebase_check_revoked,
            app=firebase_admin.get_app(),
        )
    except Exception as exc:
        logger.warning(
            "firebase_token_verification_failed error_type=%s check_revoked=%s",
            type(exc).__name__,
            settings.firebase_check_revoked,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if claims.get("aud") != settings.firebase_project_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is for another project.",
        )

    raw_role = str(claims.get("role", "applicant"))
    role = ROLE_ALIASES.get(raw_role, raw_role)
    return AuthenticatedUser(
        uid=str(claims["uid"]),
        email=claims.get("email"),
        email_verified=bool(claims.get("email_verified")),
        role=role,
        permissions=permissions_for_role(role),
    )


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
