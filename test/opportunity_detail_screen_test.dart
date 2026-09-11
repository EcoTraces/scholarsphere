import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/applications/data/demo_application_repository.dart';
import 'package:scholarsphere/features/authentication/domain/user_account.dart';
import 'package:scholarsphere/features/documents/data/demo_document_repository.dart';
import 'package:scholarsphere/features/fraud/domain/fraud_assessment.dart';
import 'package:scholarsphere/features/guidance/data/demo_application_guidance_repository.dart';
import 'package:scholarsphere/features/moderation/data/demo_moderation_repository.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/opportunities/domain/opportunity.dart';
import 'package:scholarsphere/features/opportunities/presentation/opportunity_detail_screen.dart';
import 'package:scholarsphere/features/profiles/domain/applicant_profile.dart';
import 'package:scholarsphere/features/providers/data/demo_provider_repository.dart';

Opportunity _opportunity({
  required String officialSourceUrl,
  required String applicationUrl,
}) => Opportunity(
  id: 'opp-1',
  title: 'Example Scholarship',
  provider: 'Example University',
  hostInstitution: 'Example University',
  hostCountry: 'Testland',
  type: OpportunityType.scholarship,
  funding: FundingType.fullyFunded,
  deadline: DateTime.now().add(const Duration(days: 60)),
  applicationOpenDate: DateTime.now().subtract(const Duration(days: 10)),
  verificationStatus: VerificationStatus.verified,
  lastVerifiedAt: DateTime.now(),
  officialSourceUrl: officialSourceUrl,
  applicationUrl: applicationUrl,
  eligibleNationalities: const [],
  studyLevels: const [],
  fieldsOfStudy: const [],
  summary: 'A scholarship.',
  benefits: const [],
  eligibilityRequirements: const [],
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

Widget _screen(Opportunity opportunity) {
  const user = UserAccount(
    id: 'applicant-1',
    fullName: 'Test Applicant',
    email: 'applicant@example.test',
    role: UserRole.applicant,
    status: AccountStatus.active,
    emailVerified: true,
  );
  return MaterialApp(
    home: OpportunityDetailScreen(
      opportunity: opportunity,
      profile: ApplicantProfile.empty(user),
      userId: user.id,
      applicationRepository: DemoApplicationRepository(),
      documentRepository: DemoDocumentRepository(),
      fraudAssessment: FraudAssessment(
        opportunityId: opportunity.id,
        assessedAt: DateTime.now(),
        score: 0,
        level: OverallRiskLevel.low,
        signals: const [],
      ),
      moderationRepository: DemoModerationRepository(
        DemoOpportunityRepository(),
        DemoProviderRepository(),
      ),
      guidanceRepository: DemoApplicationGuidanceRepository(),
    ),
  );
}

void main() {
  testWidgets(
    'shows one link section when the source never published a separate '
    'application page',
    (tester) async {
      await tester.pumpWidget(
        _screen(
          _opportunity(
            officialSourceUrl: 'https://example.test/program',
            applicationUrl: 'https://example.test/program',
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Official source'), findsOneWidget);
      expect(find.text('Application link'), findsNothing);
      expect(find.text('Applications are also submitted here.'), findsOneWidget);
      expect(find.text('https://example.test/program'), findsOneWidget);
    },
  );

  testWidgets(
    'shows both link sections when the application page is genuinely '
    'different from the official source',
    (tester) async {
      await tester.pumpWidget(
        _screen(
          _opportunity(
            officialSourceUrl: 'https://example.test/program',
            applicationUrl: 'https://example.test/apply',
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Official source'), findsOneWidget);
      expect(find.text('Application link'), findsOneWidget);
      expect(find.text('Applications are also submitted here.'), findsNothing);
      expect(find.text('https://example.test/program'), findsOneWidget);
      expect(find.text('https://example.test/apply'), findsOneWidget);
    },
  );
}
