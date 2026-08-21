from datetime import date

from app.models.privacy import ConsentType

_MINOR_RESTRICTED_CONSENTS = frozenset(
    {
        ConsentType.marketing,
        ConsentType.third_party_sharing,
        ConsentType.personalized_recommendations,
    }
)


def is_minor(date_of_birth: date | None, today: date) -> bool:
    """Port of PrivacyRules.isMinor() - computed server-side from the

    caller's own real ApplicantProfile.date_of_birth, never from a
    client-supplied flag (the Dart demo trusted a client-pushed
    `setMinorStatus` boolean; the live backend computes it fresh at
    consent-grant time instead, which is strictly more honest since a
    client can't misreport its own age to bypass restricted consents).
    """
    if date_of_birth is None:
        return False
    age = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age < 18


def minor_can_grant(consent_type: ConsentType) -> bool:
    return consent_type not in _MINOR_RESTRICTED_CONSENTS
