import '../domain/opportunity.dart';
import '../domain/opportunity_repository.dart';

class DemoOpportunityRepository implements OpportunityRepository {
  final List<Opportunity> _records = [..._demoOpportunities];
  final Map<String, Set<String>> _providerRecords = {};

  @override
  Future<List<Opportunity>> getPublished() async => _records
      .where((item) => item.verificationStatus == VerificationStatus.verified)
      .toList();

  @override
  Future<List<Opportunity>> getForProvider(String providerId) async {
    final ids = _providerRecords[providerId] ?? {};
    return _records.where((item) => ids.contains(item.id)).toList();
  }

  @override
  Future<void> submit({
    required String providerId,
    required Opportunity opportunity,
  }) async {
    if (opportunity.verificationStatus != VerificationStatus.pending) {
      throw ArgumentError('Provider submissions must start as pending.');
    }
    _records.add(opportunity);
    _providerRecords.putIfAbsent(providerId, () => {}).add(opportunity.id);
  }

  Future<List<Opportunity>> getVerificationCandidates() async => _records
      .where(
        (item) => {
          VerificationStatus.pending,
          VerificationStatus.incomplete,
          VerificationStatus.suspicious,
          VerificationStatus.verificationExpired,
        }.contains(item.verificationStatus),
      )
      .toList();

  Future<Opportunity?> getById(String id) async {
    for (final item in _records) {
      if (item.id == id) return item;
    }
    return null;
  }

  Future<void> replace(Opportunity opportunity) async {
    final index = _records.indexWhere((item) => item.id == opportunity.id);
    if (index == -1) throw StateError('Opportunity not found.');
    _records[index] = opportunity;
  }

  Future<void> ingestCollected(Opportunity opportunity) async {
    if (opportunity.verificationStatus != VerificationStatus.pending ||
        opportunity.lastVerifiedAt != null) {
      throw ArgumentError(
        'Collected opportunities must enter as unverified pending records.',
      );
    }
    if (_records.any((item) => item.id == opportunity.id)) {
      throw StateError('A record with this identifier already exists.');
    }
    _records.add(opportunity);
  }

  @override
  Future<List<Opportunity>> getAllForAdministration() async => [..._records];
}

final _demoOpportunities = <Opportunity>[
  Opportunity(
    id: 'global-leaders-2027',
    title: 'Global Leaders Scholarship 2027',
    provider: 'Northbridge University',
    hostInstitution: 'Northbridge University',
    hostCountry: 'United Kingdom',
    type: OpportunityType.scholarship,
    funding: FundingType.fullyFunded,
    deadline: DateTime(2027, 1, 18),
    applicationOpenDate: DateTime(2026, 9, 1),
    verificationStatus: VerificationStatus.verified,
    lastVerifiedAt: DateTime(2026, 7, 21),
    officialSourceUrl: 'https://example.edu/global-leaders',
    applicationUrl: 'https://apply.example.edu/global-leaders',
    eligibleNationalities: const ['All nationalities'],
    studyLevels: const ['Master\'s'],
    fieldsOfStudy: const ['All fields'],
    summary: 'Postgraduate funding for students with strong academic records and demonstrated community leadership.',
    benefits: const ['Full tuition', 'Living stipend', 'Return airfare'],
    eligibilityRequirements: const [
      'Open to applicants of all nationalities',
      'Bachelor\'s degree with a strong academic record',
      'Evidence of community leadership',
    ],
    requiredDocuments: const [
      'Academic transcript',
      'Curriculum vitae',
      'Personal statement',
      'Two recommendation letters',
    ],
    applicationProcedure: const [
      'Create an account on the official university portal',
      'Complete the admission and scholarship forms',
      'Upload all required documents before the deadline',
    ],
    languageRequirements: const ['English proficiency required'],
    minimumAge: null,
    maximumAge: null,
    workExperienceYearsRequired: null,
    contactInformation: 'scholarships@example.edu',
    availablePositions: 50,
    deliveryFormat: DeliveryFormat.physical,
    applicationFee: 0,
  ),
  Opportunity(
    id: 'climate-fellows-2026',
    title: 'Climate Innovation Fellowship',
    provider: 'Green Futures Foundation',
    hostInstitution: 'Green Futures Foundation',
    hostCountry: 'Germany',
    type: OpportunityType.fellowship,
    funding: FundingType.fullyFunded,
    deadline: DateTime(2026, 10, 30),
    applicationOpenDate: DateTime(2026, 7, 1),
    verificationStatus: VerificationStatus.verified,
    lastVerifiedAt: DateTime(2026, 7, 18),
    officialSourceUrl: 'https://example.org/climate-fellowship',
    applicationUrl: 'https://apply.example.org/climate-fellowship',
    eligibleNationalities: const ['Africa', 'Asia', 'Latin America'],
    studyLevels: const ['Graduate', 'Professional'],
    fieldsOfStudy: const ['Climate', 'Engineering', 'Public policy'],
    summary: 'A six-month program supporting early-career innovators working on practical climate solutions.',
    benefits: const ['Monthly stipend', 'Mentorship', 'Travel support'],
    eligibilityRequirements: const [
      'Early-career professional based in an eligible region',
      'Active climate innovation project',
    ],
    requiredDocuments: const [
      'Curriculum vitae',
      'Project summary',
      'Motivation letter',
    ],
    applicationProcedure: const [
      'Complete the official online application',
      'Submit a project summary and supporting documents',
    ],
    languageRequirements: const ['Working proficiency in English'],
    minimumAge: 21,
    maximumAge: 35,
    workExperienceYearsRequired: 1,
    contactInformation: 'fellowships@example.org',
    availablePositions: 30,
    deliveryFormat: DeliveryFormat.hybrid,
    applicationFee: 0,
  ),
  Opportunity(
    id: 'digital-policy-internship',
    title: 'Digital Policy Internship',
    provider: 'Civic Technology Network',
    hostInstitution: 'Civic Technology Network',
    hostCountry: 'Remote',
    type: OpportunityType.internship,
    funding: FundingType.partiallyFunded,
    deadline: DateTime(2026, 9, 12),
    applicationOpenDate: DateTime(2026, 6, 15),
    verificationStatus: VerificationStatus.verified,
    lastVerifiedAt: DateTime(2026, 7, 24),
    officialSourceUrl: 'https://example.net/digital-policy-internship',
    applicationUrl: 'https://careers.example.net/digital-policy-internship',
    eligibleNationalities: const ['All nationalities'],
    studyLevels: const ['Undergraduate', 'Graduate'],
    fieldsOfStudy: const ['Public policy', 'Technology', 'Law'],
    summary: 'Remote policy research placement focused on responsible technology and digital inclusion.',
    benefits: const ['Monthly allowance', 'Remote placement', 'Certificate'],
    eligibilityRequirements: const [
      'Current undergraduate or graduate student',
      'Interest in technology policy or digital inclusion',
    ],
    requiredDocuments: const ['Curriculum vitae', 'Cover letter'],
    applicationProcedure: const [
      'Submit the application through the official careers portal',
      'Shortlisted applicants complete an online interview',
    ],
    languageRequirements: const ['English'],
    minimumAge: 18,
    maximumAge: null,
    workExperienceYearsRequired: null,
    contactInformation: 'careers@example.net',
    availablePositions: 12,
    deliveryFormat: DeliveryFormat.online,
    applicationFee: 0,
  ),
  Opportunity(
    id: 'youth-research-forum',
    title: 'International Youth Research Forum',
    provider: 'Research Without Borders',
    hostInstitution: 'Research Without Borders',
    hostCountry: 'Canada',
    type: OpportunityType.conference,
    funding: FundingType.partiallyFunded,
    deadline: DateTime(2026, 11, 5),
    applicationOpenDate: DateTime(2026, 8, 1),
    verificationStatus: VerificationStatus.pending,
    lastVerifiedAt: null,
    officialSourceUrl: 'https://example.ca/youth-research-forum',
    applicationUrl: 'https://apply.example.ca/youth-research-forum',
    eligibleNationalities: const ['All nationalities'],
    studyLevels: const ['Undergraduate', 'Graduate', 'PhD'],
    fieldsOfStudy: const ['All research fields'],
    summary: 'A multidisciplinary forum for emerging researchers to present work and build international networks.',
    benefits: const ['Conference access', 'Accommodation support'],
    eligibilityRequirements: const [
      'Current undergraduate, graduate, or doctoral researcher',
      'Research abstract relevant to the forum themes',
    ],
    requiredDocuments: const ['Research abstract', 'Short biography'],
    applicationProcedure: const [
      'Submit an abstract through the official event portal',
    ],
    languageRequirements: const ['English or French'],
    minimumAge: 18,
    maximumAge: 35,
    workExperienceYearsRequired: null,
    contactInformation: 'forum@example.ca',
    availablePositions: 200,
    deliveryFormat: DeliveryFormat.physical,
    applicationFee: 25,
  ),
];
