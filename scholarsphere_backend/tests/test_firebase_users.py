"""Tests for app.services.firebase_users.

No live Firebase project is available in this environment, so every test
here mocks firebase_admin.auth.list_users directly (the officially
supported enumeration call - see the module docstring for why there is no
"query by custom claim" call to mock instead). This is the strongest
testing available without live credentials: unit tests against mocked SDK
responses, covering pagination, claim filtering, disabled users,
deduplication, empty rosters, and failure handling.

LIVE FIREBASE VERIFICATION: NOT PERFORMED. No Firebase project credentials
are available in this environment - see Task.md for what completing that
verification would require.
"""

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.services import firebase_users


@dataclass
class _FakeUser:
    uid: str
    custom_claims: dict[str, Any] | None = None
    disabled: bool = False


@dataclass
class _FakePage:
    users: list[_FakeUser]
    _next: "_FakePage | None" = field(default=None, repr=False)

    def get_next_page(self) -> "_FakePage | None":
        return self._next


def _install_fake_list_users(monkeypatch: pytest.MonkeyPatch, first_page: _FakePage) -> None:
    def fake_list_users(*, app: Any = None, max_results: int = 1000) -> _FakePage:
        return first_page

    monkeypatch.setattr(firebase_users.firebase_auth, "list_users", fake_list_users)


def test_single_page_filters_by_role(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage(
        users=[
            _FakeUser(uid="officer-1", custom_claims={"role": "verificationOfficer"}),
            _FakeUser(uid="admin-1", custom_claims={"role": "administrator"}),
            _FakeUser(uid="super-1", custom_claims={"role": "superAdministrator"}),
            _FakeUser(uid="applicant-1", custom_claims={"role": "applicant"}),
            _FakeUser(uid="moderator-1", custom_claims={"role": "moderator"}),
        ]
    )
    _install_fake_list_users(monkeypatch, page)

    uids = firebase_users.list_reverification_recipient_uids(app=object())

    assert set(uids) == {"officer-1", "admin-1", "super-1"}


def test_users_without_custom_claims_are_excluded(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage(
        users=[
            _FakeUser(uid="no-claims", custom_claims=None),
            _FakeUser(uid="empty-claims", custom_claims={}),
            _FakeUser(uid="officer-1", custom_claims={"role": "verificationOfficer"}),
        ]
    )
    _install_fake_list_users(monkeypatch, page)

    uids = firebase_users.list_reverification_recipient_uids(app=object())

    assert uids == ["officer-1"]


def test_disabled_users_are_excluded_even_with_matching_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _FakePage(
        users=[
            _FakeUser(
                uid="disabled-officer",
                custom_claims={"role": "verificationOfficer"},
                disabled=True,
            ),
            _FakeUser(uid="active-officer", custom_claims={"role": "verificationOfficer"}),
        ]
    )
    _install_fake_list_users(monkeypatch, page)

    uids = firebase_users.list_reverification_recipient_uids(app=object())

    assert uids == ["active-officer"]


def test_pagination_traverses_every_page(monkeypatch: pytest.MonkeyPatch) -> None:
    page_three = _FakePage(users=[_FakeUser(uid="officer-3", custom_claims={"role": "verificationOfficer"})])
    page_two = _FakePage(
        users=[_FakeUser(uid="officer-2", custom_claims={"role": "verificationOfficer"})],
        _next=page_three,
    )
    page_one = _FakePage(
        users=[_FakeUser(uid="officer-1", custom_claims={"role": "verificationOfficer"})],
        _next=page_two,
    )
    _install_fake_list_users(monkeypatch, page_one)

    uids = firebase_users.list_reverification_recipient_uids(app=object())

    assert uids == ["officer-1", "officer-2", "officer-3"]


def test_duplicate_uids_across_pages_are_deduplicated(monkeypatch: pytest.MonkeyPatch) -> None:
    # Not expected from a real Firebase response, but the helper must not
    # emit duplicate recipients even if it happened (e.g. a page refetch).
    page_two = _FakePage(
        users=[_FakeUser(uid="officer-1", custom_claims={"role": "verificationOfficer"})]
    )
    page_one = _FakePage(
        users=[_FakeUser(uid="officer-1", custom_claims={"role": "verificationOfficer"})],
        _next=page_two,
    )
    _install_fake_list_users(monkeypatch, page_one)

    uids = firebase_users.list_reverification_recipient_uids(app=object())

    assert uids == ["officer-1"]


def test_empty_roster_returns_empty_list_not_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage(users=[])
    _install_fake_list_users(monkeypatch, page)

    uids = firebase_users.list_reverification_recipient_uids(app=object())

    assert uids == []


def test_no_matching_role_returns_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _FakePage(
        users=[
            _FakeUser(uid="applicant-1", custom_claims={"role": "applicant"}),
            _FakeUser(uid="support-1", custom_claims={"role": "supportOfficer"}),
        ]
    )
    _install_fake_list_users(monkeypatch, page)

    uids = firebase_users.list_reverification_recipient_uids(app=object())

    assert uids == []


def test_snake_case_role_claim_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    # ROLE_ALIASES defends against a snake_case claim value even though the
    # Cloud Function (functions/index.js) sets camelCase directly today -
    # matches the same normalization get_current_user applies.
    page = _FakePage(
        users=[_FakeUser(uid="officer-1", custom_claims={"role": "verification_officer"})]
    )
    _install_fake_list_users(monkeypatch, page)

    uids = firebase_users.list_reverification_recipient_uids(app=object())

    assert uids == ["officer-1"]


def test_list_users_failure_raises_firebase_roster_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_list_users(*, app: Any = None, max_results: int = 1000) -> _FakePage:
        raise RuntimeError("simulated transport failure")

    monkeypatch.setattr(firebase_users.firebase_auth, "list_users", failing_list_users)

    with pytest.raises(firebase_users.FirebaseRosterError):
        firebase_users.list_reverification_recipient_uids(app=object())


def test_partial_pagination_failure_raises_firebase_roster_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailingPage:
        users = [_FakeUser(uid="officer-1", custom_claims={"role": "verificationOfficer"})]

        def get_next_page(self) -> None:
            raise RuntimeError("simulated failure fetching page 2")

    def fake_list_users(*, app: Any = None, max_results: int = 1000) -> _FailingPage:
        return _FailingPage()

    monkeypatch.setattr(firebase_users.firebase_auth, "list_users", fake_list_users)

    with pytest.raises(firebase_users.FirebaseRosterError):
        firebase_users.list_reverification_recipient_uids(app=object())
