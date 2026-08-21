from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.security import LoginOutcome, SecurityAlertType

_LOGIN_OUTCOME_WIRE_TO_MODEL: dict[str, LoginOutcome] = {
    "success": LoginOutcome.success,
    "invalidCredentials": LoginOutcome.invalidCredentials,
    "locked": LoginOutcome.locked,
    "blockedIp": LoginOutcome.blockedIp,
    "mfaFailed": LoginOutcome.mfaFailed,
}
_LOGIN_OUTCOME_MODEL_TO_WIRE: dict[LoginOutcome, str] = {
    value: key for key, value in _LOGIN_OUTCOME_WIRE_TO_MODEL.items()
}


def login_outcome_from_wire(value: str) -> LoginOutcome:
    try:
        return _LOGIN_OUTCOME_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown login outcome: {value!r}") from error


def login_outcome_to_wire(value: LoginOutcome) -> str:
    return _LOGIN_OUTCOME_MODEL_TO_WIRE[value]


_ALERT_TYPE_WIRE_TO_MODEL: dict[str, SecurityAlertType] = {
    "newDevice": SecurityAlertType.newDevice,
    "suspiciousLogin": SecurityAlertType.suspiciousLogin,
    "repeatedFailures": SecurityAlertType.repeatedFailures,
    "accountLocked": SecurityAlertType.accountLocked,
    "sessionRevoked": SecurityAlertType.sessionRevoked,
    "privilegedAction": SecurityAlertType.privilegedAction,
}
_ALERT_TYPE_MODEL_TO_WIRE: dict[SecurityAlertType, str] = {
    value: key for key, value in _ALERT_TYPE_WIRE_TO_MODEL.items()
}


def alert_type_to_wire(value: SecurityAlertType) -> str:
    return _ALERT_TYPE_MODEL_TO_WIRE[value]


class DeviceIdentityIn(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    browser: str = Field(min_length=1, max_length=255)
    operating_system: str = Field(min_length=1, max_length=255)


class DeviceIdentityRead(BaseModel):
    id: str
    browser: str
    operating_system: str
    ip_address: str


class CreateSessionRequest(BaseModel):
    device: DeviceIdentityIn
    strong_authentication: bool
    privileged: bool


class RecordLoginRequest(BaseModel):
    outcome: str
    device: DeviceIdentityIn

    @field_validator("outcome")
    @classmethod
    def _validate_outcome(cls, value: str) -> str:
        login_outcome_from_wire(value)
        return value


class SessionRead(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_activity_at: datetime
    revoked_at: datetime | None
    strong_authentication: bool
    device: DeviceIdentityRead

    @classmethod
    def from_model(cls, session: Any) -> "SessionRead":
        return cls(
            id=session.id,
            user_id=session.user_id,
            created_at=session.created_at,
            expires_at=session.expires_at,
            last_activity_at=session.last_activity_at,
            revoked_at=session.revoked_at,
            strong_authentication=session.strong_authentication,
            device=DeviceIdentityRead(
                id=session.device_id,
                browser=session.browser,
                operating_system=session.operating_system,
                ip_address=session.ip_address,
            ),
        )


class LoginHistoryRead(BaseModel):
    id: str
    email: str
    occurred_at: datetime
    outcome: LoginOutcome
    suspicious: bool
    device: DeviceIdentityRead

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_serializer("outcome")
    def _serialize_outcome(self, value: LoginOutcome, _info: Any) -> str:
        return login_outcome_to_wire(value)

    @classmethod
    def from_model(cls, entry: Any) -> "LoginHistoryRead":
        return cls(
            id=str(entry.id),
            email=entry.email,
            occurred_at=entry.occurred_at,
            outcome=entry.outcome,
            suspicious=entry.suspicious,
            device=DeviceIdentityRead(
                id=entry.device_id,
                browser=entry.browser,
                operating_system=entry.operating_system,
                ip_address=entry.ip_address,
            ),
        )


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    type: SecurityAlertType
    message: str
    created_at: datetime
    acknowledged_at: datetime | None

    @field_serializer("type")
    def _serialize_type(self, value: SecurityAlertType, _info: Any) -> str:
        return alert_type_to_wire(value)

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, value: Any) -> str:
        return str(value)


class RateLimitCheckRequest(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    limit: int = Field(default=60, ge=1, le=10000)
