import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/authentication/data/demo_auth_repository.dart';
import 'package:scholarsphere/features/authentication/domain/auth_repository.dart';
import 'package:scholarsphere/features/authentication/domain/user_account.dart';
import 'package:scholarsphere/features/documents/data/demo_document_repository.dart';
import 'package:scholarsphere/features/documents/domain/document_readiness.dart';
import 'package:scholarsphere/features/privacy/data/demo_privacy_repository.dart';
import 'package:scholarsphere/features/privacy/domain/privacy_models.dart';
import 'package:scholarsphere/features/privacy/domain/privacy_rules.dart';
import 'package:scholarsphere/features/security/data/demo_security_repository.dart';
import 'package:scholarsphere/features/security/domain/access_control.dart';
import 'package:scholarsphere/features/security/domain/security_models.dart';

void main() {
  const administratorEmail = 'administrator@example.test';
  const administratorPassword = 'AdministratorPass123!';
  const device = DeviceIdentity(
    id: 'test-device',
    browser: 'Test browser',
    operatingSystem: 'Test OS',
    ipAddress: '192.0.2.1',
  );

  test('permissions separate applicant and administrator capabilities', () {
    expect(
      AccessControlPolicy.allows(
        UserRole.applicant,
        Permission.manageOwnDocuments,
      ),
      isTrue,
    );
    expect(
      AccessControlPolicy.allows(UserRole.applicant, Permission.manageUsers),
      isFalse,
    );
    expect(
      AccessControlPolicy.requiresReauthentication(Permission.suspendAccounts),
      isTrue,
    );
  });

  test('five failed attempts lock subsequent login attempts', () async {
    final now = DateTime(2026, 7, 29, 10);
    final security = DemoSecurityRepository(clock: () => now);
    final auth = DemoAuthRepository(
      securityRepository: security,
      bootstrapAdminEmail: administratorEmail,
      bootstrapAdminPassword: administratorPassword,
    );

    for (var attempt = 0; attempt < 5; attempt++) {
      await expectLater(
        auth.signIn(email: administratorEmail, password: 'incorrect'),
        throwsA(isA<AuthFailure>()),
      );
    }

    await expectLater(
      auth.signIn(email: administratorEmail, password: administratorPassword),
      throwsA(
        isA<AuthFailure>().having(
          (failure) => failure.message,
          'message',
          contains('temporarily locked'),
        ),
      ),
    );
    final alerts = await security.getAlerts('test-administrator');
    expect(
      alerts.map((alert) => alert.type),
      contains(SecurityAlertType.accountLocked),
    );
  });

  test('privileged sessions require strong authentication', () async {
    final security = DemoSecurityRepository(
      clock: () => DateTime(2026, 7, 29, 10),
    );

    await expectLater(
      security.createSession(
        userId: 'admin',
        device: device,
        strongAuthentication: false,
        privileged: true,
      ),
      throwsA(isA<SecurityFailure>()),
    );
    final session = await security.createSession(
      userId: 'admin',
      device: device,
      strongAuthentication: true,
      privileged: true,
    );
    expect(
      session.expiresAt.difference(session.createdAt),
      const Duration(minutes: 15),
    );
  });

  test('only applicants can self-register', () async {
    final auth = DemoAuthRepository();

    await expectLater(
      auth.register(
        fullName: 'Provider User',
        email: 'provider@example.test',
        password: 'ProviderPass123!',
        role: UserRole.opportunityProvider,
      ),
      throwsA(
        isA<AuthFailure>().having(
          (failure) => failure.message,
          'message',
          contains('Only applicants'),
        ),
      ),
    );

    final applicant = await auth.register(
      fullName: 'Applicant User',
      email: 'applicant@example.test',
      password: 'ApplicantPass123!',
      role: UserRole.applicant,
    );
    expect(applicant.emailVerified, isFalse);
    expect(applicant.status, AccountStatus.pendingVerification);
  });

  test('administrator creates managed actor accounts', () async {
    final auth = DemoAuthRepository(
      bootstrapAdminEmail: administratorEmail,
      bootstrapAdminPassword: administratorPassword,
    );
    await auth.signIn(
      email: administratorEmail,
      password: administratorPassword,
    );

    final officer = await auth.createManagedAccount(
      fullName: 'Verification Officer',
      email: 'officer@example.test',
      temporaryPassword: 'OfficerPass123!',
      role: UserRole.verificationOfficer,
    );

    expect(officer.role, UserRole.verificationOfficer);
    expect(officer.status, AccountStatus.active);
    expect(officer.emailVerified, isTrue);
    await auth.signOut();
    expect(
      await auth.signIn(
        email: 'officer@example.test',
        password: 'OfficerPass123!',
      ),
      officer,
    );
  });

  test('third-party access needs consent and document authorization', () async {
    final privacy = DemoPrivacyRepository(clock: () => DateTime(2026, 7, 29));
    final documents = DemoDocumentRepository(privacyRepository: privacy);
    await documents.add(
      UserDocument(
        id: 'passport',
        ownerUserId: 'applicant',
        type: DocumentType.passport,
        fileName: 'passport.encrypted',
        uploadedAt: DateTime(2026, 7, 29),
        encryptedAtRest: true,
      ),
    );

    await expectLater(
      documents.grantProviderAccess(
        userId: 'applicant',
        documentId: 'passport',
        providerId: 'provider',
      ),
      throwsA(isA<PrivacyFailure>()),
    );
    await privacy.grantConsent(
      userId: 'applicant',
      type: ConsentType.thirdPartySharing,
      policyVersion: '2026-07',
    );
    await documents.grantProviderAccess(
      userId: 'applicant',
      documentId: 'passport',
      providerId: 'provider',
    );
    final document = (await documents.getForUser('applicant')).single;
    expect(document.canProviderAccess('provider'), isTrue);
    expect(document.canProviderAccess('another-provider'), isFalse);
  });

  test('minor accounts cannot enable behavioral or sharing consent', () {
    expect(
      PrivacyRules.isMinor(DateTime(2010, 1, 1), DateTime(2026, 7, 29)),
      isTrue,
    );
    expect(
      PrivacyRules.minorCanGrant(ConsentType.personalizedRecommendations),
      isFalse,
    );
    expect(PrivacyRules.minorCanGrant(ConsentType.thirdPartySharing), isFalse);
  });

  test('privacy repository rejects restricted minor consent', () async {
    final privacy = DemoPrivacyRepository();
    await privacy.setMinorStatus('minor', true);

    await expectLater(
      privacy.grantConsent(
        userId: 'minor',
        type: ConsentType.thirdPartySharing,
        policyVersion: '2026-07',
      ),
      throwsA(isA<PrivacyFailure>()),
    );
  });
}
