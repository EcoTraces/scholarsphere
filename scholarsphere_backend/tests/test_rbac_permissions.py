import pytest
from fastapi import HTTPException

from app.core.auth import ALL_PERMISSIONS, ROLE_PERMISSIONS, AuthenticatedUser, permissions_for_role
from app.core.rbac import require_permissions


def user(role: str, permissions: frozenset[str] = frozenset()) -> AuthenticatedUser:
    return AuthenticatedUser(
        uid=f"{role}-user",
        email=f"{role}@example.test",
        email_verified=True,
        role=role,
        permissions=permissions,
    )


def test_permissions_mirror_the_flutter_client_access_control_policy() -> None:
    # Mirrors lib/features/security/domain/access_control.dart exactly -
    # a change on one side without the other is the exact drift this test
    # guards against.
    assert permissions_for_role("applicant") == {
        "viewOpportunities",
        "manageOwnProfile",
        "manageOwnDocuments",
        "trackApplications",
    }
    assert permissions_for_role("opportunityProvider") == {
        "viewOpportunities",
        "submitOpportunity",
        "manageProviderOpportunities",
    }
    assert permissions_for_role("verificationOfficer") == {
        "viewOpportunities",
        "verifyOpportunity",
    }
    assert permissions_for_role("moderator") == {
        "viewOpportunities",
        "moderateContent",
    }
    assert permissions_for_role("supportOfficer") == {
        "viewOpportunities",
        "supportUsers",
    }
    assert permissions_for_role("administrator") == {
        "viewOpportunities",
        "viewAdministration",
        "manageUsers",
        "exportReports",
    }
    assert permissions_for_role("securityAdministrator") == {
        "viewAdministration",
        "manageSecurity",
        "suspendAccounts",
        "manageSecrets",
    }
    assert permissions_for_role("superAdministrator") == ALL_PERMISSIONS


def test_unknown_role_has_no_permissions() -> None:
    assert permissions_for_role("not-a-real-role") == frozenset()


def test_every_role_permission_is_a_recognized_permission() -> None:
    for role_permissions in ROLE_PERMISSIONS.values():
        assert role_permissions.issubset(ALL_PERMISSIONS)


@pytest.mark.asyncio
async def test_require_permissions_allows_a_role_with_the_permission() -> None:
    dependency = require_permissions("verifyOpportunity")
    granted = await dependency(user("verificationOfficer", permissions_for_role("verificationOfficer")))
    assert granted.role == "verificationOfficer"


@pytest.mark.asyncio
async def test_require_permissions_denies_a_role_without_the_permission() -> None:
    dependency = require_permissions("manageSecrets")
    with pytest.raises(HTTPException) as excinfo:
        await dependency(user("verificationOfficer", permissions_for_role("verificationOfficer")))
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_require_permissions_always_allows_super_administrator() -> None:
    dependency = require_permissions("manageSecrets")
    granted = await dependency(user("superAdministrator", frozenset()))
    assert granted.role == "superAdministrator"
