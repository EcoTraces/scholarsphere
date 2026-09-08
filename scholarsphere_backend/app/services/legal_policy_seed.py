"""Seeds the initial Terms & Conditions, Privacy Policy, and Cookie Policy
rows once, if no policy of that type exists yet.

Mirrors app/services/premium_plan_seed.py's pattern: a seed, not a sync -
once a policy type has a published row, an admin owns future versions
entirely via POST /legal/policies (app/api/routes/legal_compliance.py);
re-running this never overwrites or republishes over an admin's edits,
it only fills the gap for a type that has never been published.

Without this, GET /legal/policies/{type}/current returns null for every
visitor until a staff member manually publishes something - which left
the public footer's Terms/Privacy links with nothing real to show.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_compliance import LegalPolicy, LegalPolicyType
from app.services.parsing import utc_now

_TERMS_AND_CONDITIONS = """\
ScholarSphere connects applicants with scholarships, grants, fellowships, \
and internships that have been checked against their issuing institution \
before publication.

1. What ScholarSphere is
ScholarSphere is a discovery and application-preparation platform. It is \
not the scholarship, grant, or funding provider for any opportunity listed \
here, and it does not make admission, funding, visa, or selection \
decisions on behalf of any provider.

2. No guarantee of outcome
Being listed on ScholarSphere, or using ScholarSphere's application-prep \
tools, does not guarantee admission, funding, selection, a visa, or travel \
approval. Every opportunity's official requirements can change after our \
verification check; applicants must always confirm current requirements, \
deadlines, and application procedures directly on the official source \
linked from each listing before relying on them.

3. Your account
You are responsible for the accuracy of the information you provide and \
for keeping your login credentials secure. Accounts are personal and may \
not be shared or transferred.

4. Acceptable use
You agree not to use ScholarSphere to submit fraudulent applications, \
impersonate another person or organization, scrape or resell listing \
data at scale, or attempt to interfere with the platform's normal \
operation.

5. Payments
Where ScholarSphere offers a paid application-preparation package, its \
price and included features are shown before purchase. Payments are \
processed by a third-party payment provider; ScholarSphere never stores \
your full card details.

6. Content and verification
Opportunity listings go through a human verification step before \
publication, and sponsored listings are always clearly identified as \
sponsored. Verification confirms that a listing matches its official \
source at the time of the check - it is not a guarantee that the \
opportunity will remain unchanged or open indefinitely.

7. Changes to these terms
We may update these terms as the platform evolves. Material changes will \
be flagged in-app, and continued use after a material change constitutes \
acceptance of the updated terms.

8. Contact
Questions about these terms can be sent to the contact details published \
in the app's footer.
"""

_PRIVACY_POLICY = """\
This policy explains what personal data ScholarSphere collects, why, and \
how it is protected.

1. What we collect
Account information (name, email) via Firebase Authentication; profile \
details you choose to provide (nationality, field of study, and similar) \
to power matching and recommendations; documents you upload for your own \
applications; and basic usage data needed to operate the service securely \
(such as sign-in timestamps and device/browser information for fraud and \
abuse prevention).

2. How we use it
To show you relevant opportunities, to let you track and prepare \
applications, to operate the optional premium application-preparation \
package, and to keep the platform secure. We do not sell your personal \
data.

3. Document security
Uploaded application documents are encrypted at rest. Access is limited \
to you and, where you explicitly share a document with an opportunity \
provider as part of an application, that provider.

4. Personalized recommendations
Recommendations based on your profile and activity are only generated if \
you have given consent for personalized recommendations; you can withdraw \
that consent at any time from your privacy settings, after which \
recommendations fall back to non-personalized results.

5. Third parties
We use Firebase (Authentication, Firestore, Cloud Storage) for \
account and data infrastructure, and a payment provider to process any \
premium purchase. These providers process data only as needed to deliver \
their service to ScholarSphere and are bound by their own data-protection \
obligations.

6. Your rights
You can request access to, correction of, or deletion of your personal \
data, or submit a broader data-protection request, at any time through \
the contact details published in the app's footer. We respond to \
legitimate requests without unreasonable delay.

7. Data retention
We retain account and application data for as long as your account is \
active, or as needed to comply with legal obligations, after which it is \
deleted or anonymized.

8. Changes to this policy
We may update this policy as the platform evolves. Material changes will \
be flagged in-app.
"""

_COOKIE_POLICY = """\
ScholarSphere's web app uses browser storage only for what the service \
itself needs to function - it does not use third-party advertising or \
tracking cookies.

1. Strictly necessary storage
Your sign-in session (via Firebase Authentication) and basic app \
preferences (such as your last-used filters) are kept in your browser so \
the app works correctly between visits. This storage is required for the \
service to function and cannot be disabled while still using \
ScholarSphere.

2. No third-party advertising trackers
ScholarSphere does not embed third-party advertising or cross-site \
tracking cookies.

3. Analytics
Any usage analytics ScholarSphere collects are first-party and used only \
to understand and improve the platform's own features - never sold or \
shared with advertisers.

4. Managing storage
You can clear your browser's local storage/cookies for ScholarSphere at \
any time through your browser settings; doing so will simply sign you out \
and reset any locally remembered preferences.
"""

_SEEDS: dict[LegalPolicyType, tuple[str, str]] = {
    LegalPolicyType.terms_and_conditions: ("Terms & Conditions", _TERMS_AND_CONDITIONS),
    LegalPolicyType.privacy_policy: ("Privacy Policy", _PRIVACY_POLICY),
    LegalPolicyType.cookie_policy: ("Cookie Policy", _COOKIE_POLICY),
}


async def seed_default_legal_policies(session: AsyncSession) -> None:
    for policy_type, (title, content) in _SEEDS.items():
        existing = await session.scalar(
            select(LegalPolicy).where(LegalPolicy.type == policy_type)
        )
        if existing is not None:
            continue
        now = utc_now()
        session.add(
            LegalPolicy(
                id=str(uuid.uuid4()),
                type=policy_type,
                version="1.0",
                title=title,
                content=content,
                effective_at=now,
                published_at=now,
                requires_acceptance=policy_type == LegalPolicyType.terms_and_conditions
                or policy_type == LegalPolicyType.privacy_policy,
                material_change=False,
                published_by="system-seed",
            )
        )
    await session.flush()
