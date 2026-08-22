import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mocktail/mocktail.dart';
import 'package:scholarsphere/app/app.dart';
import 'package:scholarsphere/features/opportunities/data/api_opportunity_repository.dart';
import 'package:scholarsphere/features/opportunities/domain/opportunity.dart';
import 'package:scholarsphere/features/search_index/domain/search_index_repository.dart';
import 'package:scholarsphere/features/verification/data/api_verification_repository.dart';
import 'package:scholarsphere/features/authentication/data/demo_auth_repository.dart';
import 'package:scholarsphere/features/authentication/domain/user_account.dart';
import 'package:scholarsphere/features/applications/data/demo_application_repository.dart';
import 'package:scholarsphere/features/notifications/data/demo_notification_repository.dart';
import 'package:scholarsphere/features/documents/data/demo_document_repository.dart';
import 'package:scholarsphere/features/moderation/data/demo_moderation_repository.dart';
import 'package:scholarsphere/features/privacy/data/demo_privacy_repository.dart';
import 'package:scholarsphere/features/support/data/demo_support_repository.dart';
import 'package:scholarsphere/features/sources/data/demo_source_registry_repository.dart';
import 'package:scholarsphere/features/taxonomy/data/demo_taxonomy_repository.dart';
import 'package:scholarsphere/features/calendar/data/demo_calendar_repository.dart';
import 'package:scholarsphere/features/guidance/data/demo_application_guidance_repository.dart';
import 'package:scholarsphere/features/experience/data/demo_experience_repository.dart';
import 'package:scholarsphere/features/search_index/data/demo_search_index_repository.dart';
import 'package:scholarsphere/features/governance/data/demo_legal_compliance_repository.dart';
import 'package:scholarsphere/features/analytics/data/demo_analytics_repository.dart';
import 'package:scholarsphere/features/recommendations/data/demo_recommendation_governance_repository.dart';
import 'package:scholarsphere/features/provider_analytics/data/demo_provider_analytics_repository.dart';
import 'package:scholarsphere/features/security/data/demo_security_repository.dart';
import 'package:scholarsphere/features/providers/data/demo_provider_repository.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/profiles/data/demo_applicant_profile_repository.dart';
import 'package:scholarsphere/features/audit/data/demo_audit_repository.dart';
import 'package:scholarsphere/features/operations/data/demo_system_configuration_repository.dart';
import 'package:scholarsphere/features/operations/data/demo_backup_repository.dart';
import 'package:scholarsphere/features/operations/data/demo_release_repository.dart';
import 'package:scholarsphere/features/governance/data/demo_data_lifecycle_repository.dart';
import 'package:scholarsphere/features/operations/data/demo_observability_repository.dart';
import 'package:scholarsphere/features/fraud_investigation/data/demo_fraud_investigation_repository.dart';
import 'package:scholarsphere/features/collection/data/demo_opportunity_collection_repository.dart';

class _MockFirebaseAuth extends Mock implements firebase.FirebaseAuth {}

class _MockFirebaseUser extends Mock implements firebase.User {}

class _MockSearchIndexRepository extends Mock
    implements SearchIndexRepository {}

/// A fake [ApiVerificationRepository] for tests: reachable without a live
/// FastAPI backend, so the Verification Officer dashboard (which now reads
/// exclusively from this repository, not demo data -- see app.dart) can
/// still render in a widget test.
ApiVerificationRepository _fakeVerificationRepository() {
  final auth = _MockFirebaseAuth();
  final user = _MockFirebaseUser();
  when(() => auth.currentUser).thenReturn(user);
  when(() => user.getIdToken()).thenAnswer((_) async => 'test-token');
  return ApiVerificationRepository(
    baseUrl: 'https://backend.test/api/v1',
    auth: auth,
    client: MockClient((request) async {
      if (request.url.path.endsWith('/pending-verification')) {
        return http.Response(jsonEncode({'items': <dynamic>[]}), 200);
      }
      if (request.url.path.endsWith('/verification-summary')) {
        return http.Response(
          jsonEncode({
            'pending': 0,
            'verified_today': 0,
            'reverification_due_soon': 0,
            'by_status': <String, int>{},
            'official_source_ratio': 1.0,
            'decisions_last_7_days': <dynamic>[],
            'approved_by_you': 0,
          }),
          200,
        );
      }
      return http.Response('Not found', 404);
    }),
  );
}

void main() {
  // A DemoAuthRepository (in-memory, no live Firebase project required) is
  // injected into ScholarSphereApp for every test below instead of the real
  // FirebaseAuthRepository, which needs Firebase.initializeApp() to have
  // run against a real project -- something a plain `flutter test` run
  // never does. Seeded once for the whole file since each test performs
  // its own independent sign-in through the UI.
  late DemoAuthRepository authRepository;

  setUpAll(() async {
    authRepository = DemoAuthRepository(
      bootstrapAdminEmail: 'admin@scholarsphere.test',
      bootstrapAdminPassword: 'Admin123!',
    );
    await authRepository.signIn(
      email: 'admin@scholarsphere.test',
      password: 'Admin123!',
    );
    await authRepository.createManagedAccount(
      fullName: 'Support Officer',
      email: 'support@scholarsphere.test',
      temporaryPassword: 'Support1234!',
      role: UserRole.supportOfficer,
    );
    await authRepository.createManagedAccount(
      fullName: 'Security Administrator',
      email: 'security@scholarsphere.test',
      temporaryPassword: 'Security123!',
      role: UserRole.securityAdministrator,
    );
    await authRepository.createManagedAccount(
      fullName: 'Verification Officer',
      email: 'officer@scholarsphere.test',
      temporaryPassword: 'Verify12345!',
      role: UserRole.verificationOfficer,
    );
    await authRepository.createManagedAccount(
      fullName: 'Moderator',
      email: 'moderator@scholarsphere.test',
      temporaryPassword: 'Moderate123!',
      role: UserRole.moderator,
    );
    await authRepository.register(
      fullName: 'Applicant',
      email: 'scholarsphere@gmail.com',
      password: 'Scholarsphere2026!',
      role: UserRole.applicant,
    );
    // register() leaves the account pendingVerification/emailVerified:false
    // by design (real self-registration requires a real verification
    // email). Without confirming it here, every applicant-flow test below
    // lands on the "verify your email" gate instead of the dashboard, and
    // hangs pumpAndSettle() on that screen's perpetual spinner.
    await authRepository.confirmEmailVerification();
    await authRepository.signOut();
  });

  // The seeded DemoAuthRepository is shared (not recreated) across every
  // test in this file, so a session left signed-in by one test would
  // otherwise leak into the next test's fresh ScholarSphereApp instance and
  // skip its sign-in screen entirely. Force a clean, signed-out session
  // before each test.
  setUp(() async {
    await authRepository.signOut();
  });

  Future<void> signIn(WidgetTester tester) async {
    await tester.enterText(
      find.byKey(const Key('auth-email')),
      'scholarsphere@gmail.com',
    );
    await tester.enterText(
      find.byKey(const Key('auth-password')),
      'Scholarsphere2026!',
    );
    // The submit button stays disabled until the form is valid, so a frame
    // must be pumped for that state to reach the button before tapping it.
    await tester.pump();
    await tester.tap(find.byKey(const Key('auth-submit')));
    await tester.pumpAndSettle();
  }

  Future<void> openDiscovery(WidgetTester tester) async {
    await tester.tap(find.byKey(const Key('dashboard-search')));
    await tester.pumpAndSettle();
  }

  testWidgets('valid applicant credentials open applicant dashboard', (
    tester,
  ) async {
    await tester.pumpWidget(
      ScholarSphereApp(
        authRepository: authRepository,
        apiOpportunityRepository: DemoOpportunityRepository(),
        applicationRepository: DemoApplicationRepository(),
        notificationRepository: DemoNotificationRepository(),
        applicantProfileRepository: DemoApplicantProfileRepository(),
        documentRepository: DemoDocumentRepository(),
        moderationRepository: DemoModerationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        privacyRepository: DemoPrivacyRepository(),
        supportRepository: DemoSupportRepository(),
        sourceRegistryRepository: DemoSourceRegistryRepository(),
        taxonomyRepository: DemoTaxonomyRepository(),
        calendarRepository: DemoCalendarRepository(),
        guidanceRepository: DemoApplicationGuidanceRepository(),
        experienceRepository: DemoExperienceRepository(),
        searchIndexRepository: DemoSearchIndexRepository(),
        legalRepository: DemoLegalComplianceRepository(),
        analyticsRepository: DemoAnalyticsRepository(),
        recommendationGovernanceRepository:
            DemoRecommendationGovernanceRepository(),
        providerAnalyticsRepository: DemoProviderAnalyticsRepository(),
        securityRepository: DemoSecurityRepository(),
        auditRepository: DemoAuditRepository(),
        systemConfigurationRepository: DemoSystemConfigurationRepository(),
        backupRepository: DemoBackupRepository(),
        releaseRepository: DemoReleaseRepository(),
        dataLifecycleRepository: DemoDataLifecycleRepository(),
        observabilityRepository: DemoObservabilityRepository(),
        fraudInvestigationRepository: DemoFraudInvestigationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        collectionRepository: DemoOpportunityCollectionRepository(
          DemoOpportunityRepository(),
          sourceRegistry: DemoSourceRegistryRepository(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Sign in to continue and discover trusted opportunities.'),
      findsOneWidget,
    );
    await signIn(tester);

    expect(find.text('Welcome back,'), findsOneWidget);
    expect(find.text('Recommended for You'), findsOneWidget);
    expect(find.text('Upcoming Deadlines'), findsOneWidget);
  });

  testWidgets('applicant dashboard renders its desktop workspace', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ScholarSphereApp(
        authRepository: authRepository,
        apiOpportunityRepository: DemoOpportunityRepository(),
        applicationRepository: DemoApplicationRepository(),
        notificationRepository: DemoNotificationRepository(),
        applicantProfileRepository: DemoApplicantProfileRepository(),
        documentRepository: DemoDocumentRepository(),
        moderationRepository: DemoModerationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        privacyRepository: DemoPrivacyRepository(),
        supportRepository: DemoSupportRepository(),
        sourceRegistryRepository: DemoSourceRegistryRepository(),
        taxonomyRepository: DemoTaxonomyRepository(),
        calendarRepository: DemoCalendarRepository(),
        guidanceRepository: DemoApplicationGuidanceRepository(),
        experienceRepository: DemoExperienceRepository(),
        searchIndexRepository: DemoSearchIndexRepository(),
        legalRepository: DemoLegalComplianceRepository(),
        analyticsRepository: DemoAnalyticsRepository(),
        recommendationGovernanceRepository:
            DemoRecommendationGovernanceRepository(),
        providerAnalyticsRepository: DemoProviderAnalyticsRepository(),
        securityRepository: DemoSecurityRepository(),
        auditRepository: DemoAuditRepository(),
        systemConfigurationRepository: DemoSystemConfigurationRepository(),
        backupRepository: DemoBackupRepository(),
        releaseRepository: DemoReleaseRepository(),
        dataLifecycleRepository: DemoDataLifecycleRepository(),
        observabilityRepository: DemoObservabilityRepository(),
        fraudInvestigationRepository: DemoFraudInvestigationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        collectionRepository: DemoOpportunityCollectionRepository(
          DemoOpportunityRepository(),
          sourceRegistry: DemoSourceRegistryRepository(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await signIn(tester);

    expect(find.text('Dashboard'), findsOneWidget);
    expect(find.text('Application Tracker'), findsAtLeastNWidgets(1));
    expect(find.text('Recently Saved Opportunities'), findsOneWidget);
    expect(find.byKey(const Key('dashboard-search')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('administrator dashboard renders its desktop workspace', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ScholarSphereApp(
        authRepository: authRepository,
        apiOpportunityRepository: DemoOpportunityRepository(),
        applicationRepository: DemoApplicationRepository(),
        notificationRepository: DemoNotificationRepository(),
        applicantProfileRepository: DemoApplicantProfileRepository(),
        documentRepository: DemoDocumentRepository(),
        moderationRepository: DemoModerationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        privacyRepository: DemoPrivacyRepository(),
        supportRepository: DemoSupportRepository(),
        sourceRegistryRepository: DemoSourceRegistryRepository(),
        taxonomyRepository: DemoTaxonomyRepository(),
        calendarRepository: DemoCalendarRepository(),
        guidanceRepository: DemoApplicationGuidanceRepository(),
        experienceRepository: DemoExperienceRepository(),
        searchIndexRepository: DemoSearchIndexRepository(),
        legalRepository: DemoLegalComplianceRepository(),
        analyticsRepository: DemoAnalyticsRepository(),
        recommendationGovernanceRepository:
            DemoRecommendationGovernanceRepository(),
        providerAnalyticsRepository: DemoProviderAnalyticsRepository(),
        securityRepository: DemoSecurityRepository(),
        auditRepository: DemoAuditRepository(),
        systemConfigurationRepository: DemoSystemConfigurationRepository(),
        backupRepository: DemoBackupRepository(),
        releaseRepository: DemoReleaseRepository(),
        dataLifecycleRepository: DemoDataLifecycleRepository(),
        observabilityRepository: DemoObservabilityRepository(),
        fraudInvestigationRepository: DemoFraudInvestigationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        collectionRepository: DemoOpportunityCollectionRepository(
          DemoOpportunityRepository(),
          sourceRegistry: DemoSourceRegistryRepository(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('auth-email')),
      'admin@scholarsphere.test',
    );
    await tester.enterText(find.byKey(const Key('auth-password')), 'Admin123!');
    await tester.pump();
    await tester.tap(find.byKey(const Key('auth-submit')));
    await tester.pumpAndSettle();

    expect(find.text('Dashboard'), findsAtLeastNWidgets(1));
    expect(find.text('Total opportunities'), findsOneWidget);
    expect(find.text('Opportunities by Status'), findsOneWidget);
    expect(find.text('User Overview'), findsOneWidget);
    expect(find.text('System Health'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('search-index background job rebuilds from the real opportunity '
      'repository, not demo data', (tester) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final mockSearchIndex = _MockSearchIndexRepository();
    registerFallbackValue(const <Opportunity>[]);
    when(() => mockSearchIndex.rebuild(any())).thenAnswer((invocation) async {
      final opportunities =
          (invocation.positionalArguments.first as Iterable<Opportunity>)
              .toList();
      return opportunities.length;
    });

    final auth = _MockFirebaseAuth();
    final user = _MockFirebaseUser();
    when(() => auth.currentUser).thenReturn(user);
    when(() => user.getIdToken()).thenAnswer((_) async => 'test-token');
    final apiOpportunityRepository = ApiOpportunityRepository(
      baseUrl: 'https://backend.test/api/v1',
      auth: auth,
      client: MockClient((request) async {
        if (request.url.path.endsWith(
          '/external-opportunities/opportunities',
        )) {
          return http.Response(
            jsonEncode({
              'items': [
                {
                  'id': 'real-backend-opportunity-1',
                  'title': 'Real backend opportunity',
                  'provider_name': 'Example Institution',
                  'opportunity_type': 'grant',
                  'country': 'Germany',
                  'description': 'A real opportunity from the backend.',
                  'opening_date': '2026-01-01',
                  'deadline': '2026-12-31',
                  'official_source_url': 'https://example.test/real-opp-1',
                  'verification_status': 'verified',
                },
              ],
              'total': 1,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      }),
    );

    await tester.pumpWidget(
      ScholarSphereApp(
        authRepository: authRepository,
        apiOpportunityRepository: apiOpportunityRepository,
        searchIndexRepository: mockSearchIndex,
        applicationRepository: DemoApplicationRepository(),
        notificationRepository: DemoNotificationRepository(),
        applicantProfileRepository: DemoApplicantProfileRepository(),
        documentRepository: DemoDocumentRepository(),
        moderationRepository: DemoModerationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        privacyRepository: DemoPrivacyRepository(),
        supportRepository: DemoSupportRepository(),
        sourceRegistryRepository: DemoSourceRegistryRepository(),
        taxonomyRepository: DemoTaxonomyRepository(),
        calendarRepository: DemoCalendarRepository(),
        guidanceRepository: DemoApplicationGuidanceRepository(),
        experienceRepository: DemoExperienceRepository(),
        legalRepository: DemoLegalComplianceRepository(),
        analyticsRepository: DemoAnalyticsRepository(),
        recommendationGovernanceRepository:
            DemoRecommendationGovernanceRepository(),
        providerAnalyticsRepository: DemoProviderAnalyticsRepository(),
        securityRepository: DemoSecurityRepository(),
        auditRepository: DemoAuditRepository(),
        systemConfigurationRepository: DemoSystemConfigurationRepository(),
        backupRepository: DemoBackupRepository(),
        releaseRepository: DemoReleaseRepository(),
        dataLifecycleRepository: DemoDataLifecycleRepository(),
        observabilityRepository: DemoObservabilityRepository(),
        fraudInvestigationRepository: DemoFraudInvestigationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        collectionRepository: DemoOpportunityCollectionRepository(
          DemoOpportunityRepository(),
          sourceRegistry: DemoSourceRegistryRepository(),
        ),
        verificationRepository: _fakeVerificationRepository(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('auth-email')),
      'admin@scholarsphere.test',
    );
    await tester.enterText(find.byKey(const Key('auth-password')), 'Admin123!');
    await tester.pump();
    await tester.tap(find.byKey(const Key('auth-submit')));
    await tester.pumpAndSettle();

    // Mirrors what an administrator actually does to run the job: open
    // Background Jobs from the admin dashboard and process the queue.
    final backgroundJobsNav = find.text('Background Jobs');
    await tester.ensureVisible(backgroundJobsNav);
    await tester.pumpAndSettle();
    await tester.tap(backgroundJobsNav);
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Process queued jobs'));
    await tester.pumpAndSettle();

    final captured = verify(
      () => mockSearchIndex.rebuild(captureAny()),
    ).captured;
    expect(captured, isNotEmpty);
    final rebuiltWith = (captured.first as Iterable<Opportunity>).toList();
    expect(
      rebuiltWith.map((opportunity) => opportunity.id),
      contains('real-backend-opportunity-1'),
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('support officer dashboard renders its desktop workspace', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ScholarSphereApp(
        authRepository: authRepository,
        apiOpportunityRepository: DemoOpportunityRepository(),
        applicationRepository: DemoApplicationRepository(),
        notificationRepository: DemoNotificationRepository(),
        applicantProfileRepository: DemoApplicantProfileRepository(),
        documentRepository: DemoDocumentRepository(),
        moderationRepository: DemoModerationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        privacyRepository: DemoPrivacyRepository(),
        supportRepository: DemoSupportRepository(),
        sourceRegistryRepository: DemoSourceRegistryRepository(),
        taxonomyRepository: DemoTaxonomyRepository(),
        calendarRepository: DemoCalendarRepository(),
        guidanceRepository: DemoApplicationGuidanceRepository(),
        experienceRepository: DemoExperienceRepository(),
        searchIndexRepository: DemoSearchIndexRepository(),
        legalRepository: DemoLegalComplianceRepository(),
        analyticsRepository: DemoAnalyticsRepository(),
        recommendationGovernanceRepository:
            DemoRecommendationGovernanceRepository(),
        providerAnalyticsRepository: DemoProviderAnalyticsRepository(),
        securityRepository: DemoSecurityRepository(),
        auditRepository: DemoAuditRepository(),
        systemConfigurationRepository: DemoSystemConfigurationRepository(),
        backupRepository: DemoBackupRepository(),
        releaseRepository: DemoReleaseRepository(),
        dataLifecycleRepository: DemoDataLifecycleRepository(),
        observabilityRepository: DemoObservabilityRepository(),
        fraudInvestigationRepository: DemoFraudInvestigationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        collectionRepository: DemoOpportunityCollectionRepository(
          DemoOpportunityRepository(),
          sourceRegistry: DemoSourceRegistryRepository(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('auth-email')),
      'support@scholarsphere.test',
    );
    await tester.enterText(
      find.byKey(const Key('auth-password')),
      'Support1234!',
    );
    await tester.pump();
    await tester.tap(find.byKey(const Key('auth-submit')));
    await tester.pumpAndSettle();

    expect(find.text('Dashboard'), findsAtLeastNWidgets(1));
    expect(find.text('Open Tickets'), findsOneWidget);
    expect(find.text('Recent Tickets'), findsOneWidget);
    expect(find.text('Tickets by Status'), findsOneWidget);
    expect(find.text('Performance Overview'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'security administrator dashboard renders its desktop workspace',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        ScholarSphereApp(
          authRepository: authRepository,
          apiOpportunityRepository: DemoOpportunityRepository(),
          applicationRepository: DemoApplicationRepository(),
          notificationRepository: DemoNotificationRepository(),
          applicantProfileRepository: DemoApplicantProfileRepository(),
          documentRepository: DemoDocumentRepository(),
          moderationRepository: DemoModerationRepository(
            DemoOpportunityRepository(),
            DemoProviderRepository(),
          ),
          privacyRepository: DemoPrivacyRepository(),
          supportRepository: DemoSupportRepository(),
          sourceRegistryRepository: DemoSourceRegistryRepository(),
          taxonomyRepository: DemoTaxonomyRepository(),
          calendarRepository: DemoCalendarRepository(),
          guidanceRepository: DemoApplicationGuidanceRepository(),
          experienceRepository: DemoExperienceRepository(),
          searchIndexRepository: DemoSearchIndexRepository(),
          legalRepository: DemoLegalComplianceRepository(),
          analyticsRepository: DemoAnalyticsRepository(),
          recommendationGovernanceRepository:
              DemoRecommendationGovernanceRepository(),
          providerAnalyticsRepository: DemoProviderAnalyticsRepository(),
          securityRepository: DemoSecurityRepository(),
          auditRepository: DemoAuditRepository(),
          systemConfigurationRepository: DemoSystemConfigurationRepository(),
          backupRepository: DemoBackupRepository(),
          releaseRepository: DemoReleaseRepository(),
          dataLifecycleRepository: DemoDataLifecycleRepository(),
          observabilityRepository: DemoObservabilityRepository(),
          fraudInvestigationRepository: DemoFraudInvestigationRepository(
            DemoOpportunityRepository(),
            DemoProviderRepository(),
          ),
          collectionRepository: DemoOpportunityCollectionRepository(
            DemoOpportunityRepository(),
            sourceRegistry: DemoSourceRegistryRepository(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('auth-email')),
        'security@scholarsphere.test',
      );
      await tester.enterText(
        find.byKey(const Key('auth-password')),
        'Security123!',
      );
      await tester.pump();
      await tester.tap(find.byKey(const Key('auth-submit')));
      await tester.pumpAndSettle();

      expect(find.text('Security Dashboard'), findsOneWidget);
      expect(find.text('Login Attempts'), findsAtLeastNWidgets(1));
      expect(find.text('Top Threats by Type'), findsOneWidget);
      expect(find.text('MFA Adoption'), findsOneWidget);
      expect(find.text('Security Alerts Summary'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('verification officer dashboard renders its desktop workspace', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ScholarSphereApp(
        authRepository: authRepository,
        apiOpportunityRepository: DemoOpportunityRepository(),
        applicationRepository: DemoApplicationRepository(),
        notificationRepository: DemoNotificationRepository(),
        applicantProfileRepository: DemoApplicantProfileRepository(),
        documentRepository: DemoDocumentRepository(),
        moderationRepository: DemoModerationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        privacyRepository: DemoPrivacyRepository(),
        supportRepository: DemoSupportRepository(),
        sourceRegistryRepository: DemoSourceRegistryRepository(),
        taxonomyRepository: DemoTaxonomyRepository(),
        calendarRepository: DemoCalendarRepository(),
        guidanceRepository: DemoApplicationGuidanceRepository(),
        experienceRepository: DemoExperienceRepository(),
        searchIndexRepository: DemoSearchIndexRepository(),
        legalRepository: DemoLegalComplianceRepository(),
        analyticsRepository: DemoAnalyticsRepository(),
        recommendationGovernanceRepository:
            DemoRecommendationGovernanceRepository(),
        providerAnalyticsRepository: DemoProviderAnalyticsRepository(),
        securityRepository: DemoSecurityRepository(),
        auditRepository: DemoAuditRepository(),
        systemConfigurationRepository: DemoSystemConfigurationRepository(),
        backupRepository: DemoBackupRepository(),
        releaseRepository: DemoReleaseRepository(),
        dataLifecycleRepository: DemoDataLifecycleRepository(),
        observabilityRepository: DemoObservabilityRepository(),
        fraudInvestigationRepository: DemoFraudInvestigationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        collectionRepository: DemoOpportunityCollectionRepository(
          DemoOpportunityRepository(),
          sourceRegistry: DemoSourceRegistryRepository(),
        ),
        verificationRepository: _fakeVerificationRepository(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('auth-email')),
      'officer@scholarsphere.test',
    );
    await tester.enterText(
      find.byKey(const Key('auth-password')),
      'Verify12345!',
    );
    await tester.pump();
    await tester.tap(find.byKey(const Key('auth-submit')));
    await tester.pumpAndSettle();

    expect(
      find.text('Security Verification Officer Dashboard'),
      findsOneWidget,
    );
    expect(find.text('Pending Verification'), findsOneWidget);
    expect(find.text('Approved by You'), findsOneWidget);
    expect(find.text('Verification Queue Overview'), findsOneWidget);
    expect(find.text('Verification Activity (last 7 days)'), findsOneWidget);
    expect(find.text('Pending Queue'), findsOneWidget);
    expect(find.text('Source Reliability'), findsAtLeastNWidgets(1));
    expect(tester.takeException(), isNull);
  });

  testWidgets('moderator dashboard renders its desktop workspace', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ScholarSphereApp(
        authRepository: authRepository,
        apiOpportunityRepository: DemoOpportunityRepository(),
        applicationRepository: DemoApplicationRepository(),
        notificationRepository: DemoNotificationRepository(),
        applicantProfileRepository: DemoApplicantProfileRepository(),
        documentRepository: DemoDocumentRepository(),
        moderationRepository: DemoModerationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        privacyRepository: DemoPrivacyRepository(),
        supportRepository: DemoSupportRepository(),
        sourceRegistryRepository: DemoSourceRegistryRepository(),
        taxonomyRepository: DemoTaxonomyRepository(),
        calendarRepository: DemoCalendarRepository(),
        guidanceRepository: DemoApplicationGuidanceRepository(),
        experienceRepository: DemoExperienceRepository(),
        searchIndexRepository: DemoSearchIndexRepository(),
        legalRepository: DemoLegalComplianceRepository(),
        analyticsRepository: DemoAnalyticsRepository(),
        recommendationGovernanceRepository:
            DemoRecommendationGovernanceRepository(),
        providerAnalyticsRepository: DemoProviderAnalyticsRepository(),
        securityRepository: DemoSecurityRepository(),
        auditRepository: DemoAuditRepository(),
        systemConfigurationRepository: DemoSystemConfigurationRepository(),
        backupRepository: DemoBackupRepository(),
        releaseRepository: DemoReleaseRepository(),
        dataLifecycleRepository: DemoDataLifecycleRepository(),
        observabilityRepository: DemoObservabilityRepository(),
        fraudInvestigationRepository: DemoFraudInvestigationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        collectionRepository: DemoOpportunityCollectionRepository(
          DemoOpportunityRepository(),
          sourceRegistry: DemoSourceRegistryRepository(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('auth-email')),
      'moderator@scholarsphere.test',
    );
    await tester.enterText(
      find.byKey(const Key('auth-password')),
      'Moderate123!',
    );
    await tester.pump();
    await tester.tap(find.byKey(const Key('auth-submit')));
    await tester.pumpAndSettle();

    expect(find.text('Moderator Dashboard'), findsOneWidget);
    expect(find.text('New Reports'), findsOneWidget);
    expect(find.text('Reports by Category'), findsOneWidget);
    expect(find.text('Recent Reports'), findsOneWidget);
    expect(find.text('Community Reminders'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('discovery shows verified opportunities and filters by search', (
    tester,
  ) async {
    await tester.pumpWidget(
      ScholarSphereApp(
        authRepository: authRepository,
        apiOpportunityRepository: DemoOpportunityRepository(),
        applicationRepository: DemoApplicationRepository(),
        notificationRepository: DemoNotificationRepository(),
        applicantProfileRepository: DemoApplicantProfileRepository(),
        documentRepository: DemoDocumentRepository(),
        moderationRepository: DemoModerationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        privacyRepository: DemoPrivacyRepository(),
        supportRepository: DemoSupportRepository(),
        sourceRegistryRepository: DemoSourceRegistryRepository(),
        taxonomyRepository: DemoTaxonomyRepository(),
        calendarRepository: DemoCalendarRepository(),
        guidanceRepository: DemoApplicationGuidanceRepository(),
        experienceRepository: DemoExperienceRepository(),
        searchIndexRepository: DemoSearchIndexRepository(),
        legalRepository: DemoLegalComplianceRepository(),
        analyticsRepository: DemoAnalyticsRepository(),
        recommendationGovernanceRepository:
            DemoRecommendationGovernanceRepository(),
        providerAnalyticsRepository: DemoProviderAnalyticsRepository(),
        securityRepository: DemoSecurityRepository(),
        auditRepository: DemoAuditRepository(),
        systemConfigurationRepository: DemoSystemConfigurationRepository(),
        backupRepository: DemoBackupRepository(),
        releaseRepository: DemoReleaseRepository(),
        dataLifecycleRepository: DemoDataLifecycleRepository(),
        observabilityRepository: DemoObservabilityRepository(),
        fraudInvestigationRepository: DemoFraudInvestigationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        collectionRepository: DemoOpportunityCollectionRepository(
          DemoOpportunityRepository(),
          sourceRegistry: DemoSourceRegistryRepository(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await signIn(tester);
    await openDiscovery(tester);

    expect(find.text('Find your next opportunity'), findsOneWidget);
    expect(find.text('3 opportunities'), findsOneWidget);
    expect(find.text('Global Leaders Scholarship 2027'), findsOneWidget);

    await tester.enterText(
      find.byKey(const Key('opportunity-search')),
      'climate',
    );
    await tester.pump();

    expect(find.text('1 opportunities'), findsOneWidget);
    expect(find.text('Climate Innovation Fellowship'), findsOneWidget);
    expect(find.text('Global Leaders Scholarship 2027'), findsNothing);
  });

  testWidgets('opportunity details expose verification evidence', (
    tester,
  ) async {
    await tester.pumpWidget(
      ScholarSphereApp(
        authRepository: authRepository,
        apiOpportunityRepository: DemoOpportunityRepository(),
        applicationRepository: DemoApplicationRepository(),
        notificationRepository: DemoNotificationRepository(),
        applicantProfileRepository: DemoApplicantProfileRepository(),
        documentRepository: DemoDocumentRepository(),
        moderationRepository: DemoModerationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        privacyRepository: DemoPrivacyRepository(),
        supportRepository: DemoSupportRepository(),
        sourceRegistryRepository: DemoSourceRegistryRepository(),
        taxonomyRepository: DemoTaxonomyRepository(),
        calendarRepository: DemoCalendarRepository(),
        guidanceRepository: DemoApplicationGuidanceRepository(),
        experienceRepository: DemoExperienceRepository(),
        searchIndexRepository: DemoSearchIndexRepository(),
        legalRepository: DemoLegalComplianceRepository(),
        analyticsRepository: DemoAnalyticsRepository(),
        recommendationGovernanceRepository:
            DemoRecommendationGovernanceRepository(),
        providerAnalyticsRepository: DemoProviderAnalyticsRepository(),
        securityRepository: DemoSecurityRepository(),
        auditRepository: DemoAuditRepository(),
        systemConfigurationRepository: DemoSystemConfigurationRepository(),
        backupRepository: DemoBackupRepository(),
        releaseRepository: DemoReleaseRepository(),
        dataLifecycleRepository: DemoDataLifecycleRepository(),
        observabilityRepository: DemoObservabilityRepository(),
        fraudInvestigationRepository: DemoFraudInvestigationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        collectionRepository: DemoOpportunityCollectionRepository(
          DemoOpportunityRepository(),
          sourceRegistry: DemoSourceRegistryRepository(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await signIn(tester);
    await openDiscovery(tester);

    final opportunity = find.text('Global Leaders Scholarship 2027');
    await tester.ensureVisible(opportunity);
    await tester.pumpAndSettle();
    await tester.tap(opportunity);
    await tester.pumpAndSettle();

    expect(
      find.text('Verified from the official source on 21 July 2026.'),
      findsOneWidget,
    );
    expect(find.textContaining('Eligibility score:'), findsOneWidget);
    expect(
      find.textContaining('No automated safety warnings detected'),
      findsOneWidget,
    );
    expect(find.text('Eligibility'), findsOneWidget);
    expect(find.text('Required documents'), findsOneWidget);
    expect(find.text('How to apply'), findsOneWidget);
    expect(find.text('https://example.edu/global-leaders'), findsOneWidget);
  });

  testWidgets('applicant can open the private profile editor', (tester) async {
    await tester.pumpWidget(
      ScholarSphereApp(
        authRepository: authRepository,
        apiOpportunityRepository: DemoOpportunityRepository(),
        applicationRepository: DemoApplicationRepository(),
        notificationRepository: DemoNotificationRepository(),
        applicantProfileRepository: DemoApplicantProfileRepository(),
        documentRepository: DemoDocumentRepository(),
        moderationRepository: DemoModerationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        privacyRepository: DemoPrivacyRepository(),
        supportRepository: DemoSupportRepository(),
        sourceRegistryRepository: DemoSourceRegistryRepository(),
        taxonomyRepository: DemoTaxonomyRepository(),
        calendarRepository: DemoCalendarRepository(),
        guidanceRepository: DemoApplicationGuidanceRepository(),
        experienceRepository: DemoExperienceRepository(),
        searchIndexRepository: DemoSearchIndexRepository(),
        legalRepository: DemoLegalComplianceRepository(),
        analyticsRepository: DemoAnalyticsRepository(),
        recommendationGovernanceRepository:
            DemoRecommendationGovernanceRepository(),
        providerAnalyticsRepository: DemoProviderAnalyticsRepository(),
        securityRepository: DemoSecurityRepository(),
        auditRepository: DemoAuditRepository(),
        systemConfigurationRepository: DemoSystemConfigurationRepository(),
        backupRepository: DemoBackupRepository(),
        releaseRepository: DemoReleaseRepository(),
        dataLifecycleRepository: DemoDataLifecycleRepository(),
        observabilityRepository: DemoObservabilityRepository(),
        fraudInvestigationRepository: DemoFraudInvestigationRepository(
          DemoOpportunityRepository(),
          DemoProviderRepository(),
        ),
        collectionRepository: DemoOpportunityCollectionRepository(
          DemoOpportunityRepository(),
          sourceRegistry: DemoSourceRegistryRepository(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await signIn(tester);

    await tester.tap(find.byTooltip('Account'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Edit profile'));
    await tester.pumpAndSettle();

    expect(find.text('Applicant profile'), findsOneWidget);
    expect(find.textContaining('Your profile is private'), findsOneWidget);
    expect(find.text('Education and experience'), findsOneWidget);
    expect(find.text('Uploaded documents'), findsOneWidget);
  });
}
