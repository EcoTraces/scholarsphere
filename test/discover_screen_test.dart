import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/analytics/data/demo_analytics_repository.dart';
import 'package:scholarsphere/features/applications/data/demo_application_repository.dart';
import 'package:scholarsphere/features/authentication/domain/user_account.dart';
import 'package:scholarsphere/features/calendar/data/demo_calendar_repository.dart';
import 'package:scholarsphere/features/documents/data/demo_document_repository.dart';
import 'package:scholarsphere/features/experience/data/demo_experience_repository.dart';
import 'package:scholarsphere/features/guidance/data/demo_application_guidance_repository.dart';
import 'package:scholarsphere/features/moderation/data/demo_moderation_repository.dart';
import 'package:scholarsphere/features/notifications/data/demo_notification_repository.dart';
import 'package:scholarsphere/features/opportunities/domain/opportunity.dart';
import 'package:scholarsphere/features/opportunities/domain/opportunity_repository.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/opportunities/presentation/discover_screen.dart';
import 'package:scholarsphere/features/privacy/data/demo_privacy_repository.dart';
import 'package:scholarsphere/features/profiles/data/demo_applicant_profile_repository.dart';
import 'package:scholarsphere/features/providers/data/demo_provider_repository.dart';
import 'package:scholarsphere/features/recommendations/data/demo_recommendation_governance_repository.dart';
import 'package:scholarsphere/features/search_index/data/demo_search_index_repository.dart';
import 'package:scholarsphere/features/security/data/demo_security_repository.dart';
import 'package:scholarsphere/features/support/data/demo_support_repository.dart';

/// Mirrors exactly what ApiOpportunityRepository._toOpportunity produces
/// for a real, live-imported backend record: several structured fields
/// (studyLevels among them) are honestly left empty rather than
/// fabricated, since many real sources never had that data to extract.
Opportunity _realWorldShapedOpportunity() => Opportunity(
  id: 'real-1',
  title: 'Real Backend Opportunity With No Study Level Data',
  provider: 'Some Ministry',
  hostInstitution: 'Some Ministry',
  hostCountry: 'Testland',
  type: OpportunityType.grant,
  funding: FundingType.partiallyFunded,
  deadline: DateTime.now().add(const Duration(days: 60)),
  applicationOpenDate: DateTime.now().subtract(const Duration(days: 10)),
  verificationStatus: VerificationStatus.verified,
  lastVerifiedAt: DateTime.now(),
  officialSourceUrl: 'https://example.test/opportunity',
  applicationUrl: 'https://example.test/opportunity/apply',
  eligibleNationalities: const [],
  studyLevels: const [],
  fieldsOfStudy: const [],
  summary: 'A real opportunity imported without structured study levels.',
  benefits: const [],
  eligibilityRequirements: const [
    'Eligibility criteria are not yet structured for this source.',
  ],
  requiredDocuments: const [],
  applicationProcedure: const [],
  languageRequirements: const [],
  minimumAge: null,
  maximumAge: null,
  workExperienceYearsRequired: null,
  contactInformation: '',
  availablePositions: null,
  deliveryFormat: DeliveryFormat.online,
);

/// Same shape as [_realWorldShapedOpportunity], but for a source that
/// genuinely researched full funding coverage (e.g. Knight-Hennessy
/// Scholars, Maastricht's NL-High Potential scholarship) - the Discover
/// card must reflect that real value rather than the previous hardcoded
/// "Partially funded" every record used to show regardless of its
/// actual funding_type.
Opportunity _fullyFundedOpportunity() => Opportunity(
  id: 'real-2',
  title: 'Real Backend Opportunity That Is Fully Funded',
  provider: 'Some University',
  hostInstitution: 'Some University',
  hostCountry: 'Testland',
  type: OpportunityType.scholarship,
  funding: FundingType.fullyFunded,
  deadline: DateTime.now().add(const Duration(days: 60)),
  applicationOpenDate: DateTime.now().subtract(const Duration(days: 10)),
  verificationStatus: VerificationStatus.verified,
  lastVerifiedAt: DateTime.now(),
  officialSourceUrl: 'https://example.test/fully-funded',
  applicationUrl: 'https://example.test/fully-funded',
  eligibleNationalities: const [],
  studyLevels: const [],
  fieldsOfStudy: const [],
  summary: 'A real, genuinely fully-funded opportunity.',
  benefits: const [],
  eligibilityRequirements: const [
    'Eligibility criteria are not yet structured for this source.',
  ],
  requiredDocuments: const [],
  applicationProcedure: const [],
  languageRequirements: const [],
  minimumAge: null,
  maximumAge: null,
  workExperienceYearsRequired: null,
  contactInformation: '',
  availablePositions: null,
  deliveryFormat: DeliveryFormat.online,
);

class _FakeOpportunityRepository implements OpportunityRepository {
  const _FakeOpportunityRepository({required this.opportunities});

  final List<Opportunity> opportunities;

  @override
  Future<List<Opportunity>> getPublished() async => opportunities;

  @override
  Future<List<Opportunity>> getForProvider(String providerId) async => [];

  @override
  Future<void> submit({
    required String providerId,
    required Opportunity opportunity,
  }) async {}

  @override
  Future<List<Opportunity>> getAllForAdministration() async => [];
}

void main() {
  testWidgets(
    'a real opportunity with no structured study level renders its card '
    'instead of crashing into a blank tile',
    (tester) async {
      const user = UserAccount(
        id: 'applicant-1',
        fullName: 'Test Applicant',
        email: 'applicant@example.test',
        role: UserRole.applicant,
        status: AccountStatus.active,
        emailVerified: true,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: DiscoverScreen(
            repository: _FakeOpportunityRepository(
              opportunities: [_realWorldShapedOpportunity()],
            ),
            profileRepository: DemoApplicantProfileRepository(),
            notificationRepository: DemoNotificationRepository(),
            applicationRepository: DemoApplicationRepository(),
            documentRepository: DemoDocumentRepository(),
            analyticsRepository: DemoAnalyticsRepository(),
            securityRepository: DemoSecurityRepository(),
            privacyRepository: DemoPrivacyRepository(),
            recommendationGovernanceRepository:
                DemoRecommendationGovernanceRepository(),
            moderationRepository: DemoModerationRepository(
              DemoOpportunityRepository(),
              DemoProviderRepository(),
            ),
            experienceRepository: DemoExperienceRepository(),
            onExperienceChanged: (_) {},
            searchIndexRepository: DemoSearchIndexRepository(),
            supportRepository: DemoSupportRepository(),
            calendarRepository: DemoCalendarRepository(),
            guidanceRepository: DemoApplicationGuidanceRepository(),
            user: user,
            onSignOut: () {},
          ),
        ),
      );
      await tester.pumpAndSettle();

      // No exception was thrown during build (tester.pumpAndSettle would
      // have surfaced one) and the real title/funding chip render - the
      // only thing honestly omitted is the study-level chip, since there
      // is no real study level data for this record.
      expect(
        find.text('Real Backend Opportunity With No Study Level Data'),
        findsOneWidget,
      );
      expect(find.text('Partially funded'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'a real, genuinely fully-funded opportunity shows a Fully funded chip '
    'on its Discover card, not the previous hardcoded Partially funded',
    (tester) async {
      const user = UserAccount(
        id: 'applicant-1',
        fullName: 'Test Applicant',
        email: 'applicant@example.test',
        role: UserRole.applicant,
        status: AccountStatus.active,
        emailVerified: true,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: DiscoverScreen(
            repository: _FakeOpportunityRepository(
              opportunities: [_fullyFundedOpportunity()],
            ),
            profileRepository: DemoApplicantProfileRepository(),
            notificationRepository: DemoNotificationRepository(),
            applicationRepository: DemoApplicationRepository(),
            documentRepository: DemoDocumentRepository(),
            analyticsRepository: DemoAnalyticsRepository(),
            securityRepository: DemoSecurityRepository(),
            privacyRepository: DemoPrivacyRepository(),
            recommendationGovernanceRepository:
                DemoRecommendationGovernanceRepository(),
            moderationRepository: DemoModerationRepository(
              DemoOpportunityRepository(),
              DemoProviderRepository(),
            ),
            experienceRepository: DemoExperienceRepository(),
            onExperienceChanged: (_) {},
            searchIndexRepository: DemoSearchIndexRepository(),
            supportRepository: DemoSupportRepository(),
            calendarRepository: DemoCalendarRepository(),
            guidanceRepository: DemoApplicationGuidanceRepository(),
            user: user,
            onSignOut: () {},
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.text('Real Backend Opportunity That Is Fully Funded'),
        findsOneWidget,
      );
      expect(find.text('Fully funded'), findsOneWidget);
      expect(find.text('Partially funded'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );
}
