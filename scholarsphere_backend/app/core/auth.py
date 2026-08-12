import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

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

    raw_permissions = claims.get("permissions", [])
    permissions = (
        frozenset(str(item) for item in raw_permissions)
        if isinstance(raw_permissions, list)
        else frozenset()
    )
    raw_role = str(claims.get("role", "applicant"))
    return AuthenticatedUser(
        uid=str(claims["uid"]),
        email=claims.get("email"),
        email_verified=bool(claims.get("email_verified")),
        role=ROLE_ALIASES.get(raw_role, raw_role),
        permissions=permissions,
    )


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
