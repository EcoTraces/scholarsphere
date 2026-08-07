import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/fraud/domain/fraud_assessment.dart';
import 'package:scholarsphere/features/fraud/domain/fraud_detection_service.dart';
import 'package:scholarsphere/features/opportunities/domain/opportunity.dart';

void main() {
  final service = FraudDetectionService(clock: () => DateTime(2026, 7, 29));

  test('dangerous content and record inconsistencies produce typed signals', () {
    final opportunity = _opportunity(
      provider: 'Unconfirmed sponsor',
      institution: 'Unknown',
      openDate: DateTime(2026, 12, 1),
      deadline: DateTime(2026, 11, 1),
      sourceUrl: 'http://offers.example/scholarship',
      applicationUrl: 'https://bit.ly/apply-now',
      summary:
          'Guaranteed selection and an unlimited stipend for every applicant.',
      procedure: const [
        'Send payment directly to a personal bank account.',
        'Provide your password and online banking credentials.',
      ],
    );

    final assessment = service.assess(opportunity);
    final types = assessment.signals.map((item) => item.type).toSet();

    expect(types, contains(FraudSignalType.personalAccountPayment));
    expect(types, contains(FraudSignalType.unofficialDomain));
    expect(types, contains(FraudSignalType.guaranteedSelection));
    expect(types, contains(FraudSignalType.credentialRequest));
    expect(types, contains(FraudSignalType.inconsistentDeadline));
    expect(types, contains(FraudSignalType.shortenedLink));
    expect(types, contains(FraudSignalType.unrealisticBenefits));
    expect(types, contains(FraudSignalType.missingSponsor));
    expect(assessment.level, OverallRiskLevel.critical);
  });

  test('established institution on an unexpected domain is flagged', () {
    final opportunity = _opportunity(
      title: 'Harvard University Global Scholarship',
      provider: 'Harvard University',
      institution: 'Harvard University',
      sourceUrl: 'https://harvard-awards.example/program',
      applicationUrl: 'https://harvard-awards.example/apply',
    );

    final assessment = service.assess(opportunity);

    expect(
      assessment.signals.map((item) => item.type),
      contains(FraudSignalType.institutionImpersonation),
    );
  });

  test('duplicate identity with an altered application domain is flagged', () {
    final legitimate = _opportunity(
      id: 'legitimate',
      sourceUrl: 'https://official.example/program',
      applicationUrl: 'https://apply.official.example/program',
    );
    final duplicate = _opportunity(
      id: 'duplicate',
      sourceUrl: 'https://official.example/program',
      applicationUrl: 'https://altered.example/apply',
    );

    final assessment = service.assess(
      duplicate,
      knownOpportunities: [legitimate],
    );

    expect(
      assessment.signals.map((item) => item.type),
      contains(FraudSignalType.alteredLinkDuplicate),
    );
  });

  test('signals use caution language rather than unsupported accusations', () {
    final opportunity = _opportunity(
      sourceUrl: 'https://official.example/program',
      applicationUrl: 'https://different.example/apply',
    );

    final assessment = service.assess(opportunity);

    expect(assessment.hasWarnings, isTrue);
    expect(
      assessment.signals.every(
        (signal) => !signal.userMessage.toLowerCase().contains('is a scam'),
      ),
      isTrue,
    );
  });
}

Opportunity _opportunity({
  String id = 'opportunity',
  String title = 'Global Scholarship',
  String provider = 'Official Foundation',
  String institution = 'Official University',
  DateTime? openDate,
  DateTime? deadline,
  String sourceUrl = 'https://official.example/program',
  String applicationUrl = 'https://apply.official.example/program',
  String summary = 'Competitive scholarship selected through formal review.',
  List<String> procedure = const ['Apply through the official portal.'],
}) => Opportunity(
  id: id,
  title: title,
  provider: provider,
  hostInstitution: institution,
  hostCountry: 'Global',
  type: OpportunityType.scholarship,
  funding: FundingType.fullyFunded,
  deadline: deadline ?? DateTime(2027, 1, 1),
  applicationOpenDate: openDate ?? DateTime(2026, 8, 1),
  verificationStatus: VerificationStatus.pending,
  lastVerifiedAt: null,
  officialSourceUrl: sourceUrl,
  applicationUrl: applicationUrl,
  eligibleNationalities: const ['All nationalities'],
  studyLevels: const ['Master\'s'],
  fieldsOfStudy: const ['All fields'],
  summary: summary,
  benefits: const ['Tuition'],
  eligibilityRequirements: const ['Academic merit'],
  requiredDocuments: const ['Transcript'],
  applicationProcedure: procedure,
  languageRequirements: const ['English'],
  minimumAge: null,
  maximumAge: null,
  workExperienceYearsRequired: null,
  contactInformation: 'awards@official.example',
  availablePositions: 10,
  deliveryFormat: DeliveryFormat.physical,
  applicationFee: 0,
);
