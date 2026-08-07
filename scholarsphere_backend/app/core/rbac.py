from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.core.auth import AuthenticatedUser, get_current_user

STAFF_ROLES = frozenset(
    {
        "verificationOfficer",
        "moderator",
        "supportOfficer",
        "administrator",
        "securityAdministrator",
        "superAdministrator",
    }
)


def require_roles(*roles: str) -> Callable[..., AuthenticatedUser]:
    allowed = frozenset(roles)

    async def dependency(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role is not authorized for this action.",
            )
        return user

    return dependency


def require_permissions(*permissions: str) -> Callable[..., AuthenticatedUser]:
    required = frozenset(permissions)

    async def dependency(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if user.role == "superAdministrator":
            return user
        if not required.issubset(user.permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Required permission is missing.",
            )
        return user

    return dependency
