enum OpportunityType {
  scholarship,
  fellowship,
  internship,
  conference,
  summit,
  webinar,
  exchangeProgram,
  researchGrant,
  competition,
  training,
  volunteering,
  youthProgram,
  onlineCourse,
  fundedEvent,
  grant,
  job,
}

enum FundingType { fullyFunded, partiallyFunded, selfFunded }

enum VerificationStatus {
  pending,
  verified,
  verificationExpired,
  incomplete,
  suspicious,
  rejected,
  expired,
  archived,
}

enum DeliveryFormat { online, physical, hybrid }

class Opportunity {
  const Opportunity({
    required this.id,
    required this.title,
    required this.provider,
    required this.hostInstitution,
    required this.hostCountry,
    required this.type,
    required this.funding,
    required this.deadline,
    required this.applicationOpenDate,
    required this.verificationStatus,
    required this.lastVerifiedAt,
    required this.officialSourceUrl,
    required this.applicationUrl,
    required this.eligibleNationalities,
    required this.studyLevels,
    required this.fieldsOfStudy,
    required this.summary,
    required this.benefits,
    required this.eligibilityRequirements,
    required this.requiredDocuments,
    required this.applicationProcedure,
    required this.languageRequirements,
    required this.minimumAge,
    required this.maximumAge,
    required this.workExperienceYearsRequired,
    required this.contactInformation,
    required this.availablePositions,
    required this.deliveryFormat,
    this.applicationFee,
  });

  final String id;
  final String title;
  final String provider;
  final String hostInstitution;
  final String hostCountry;
  final OpportunityType type;
  final FundingType funding;
  final DateTime deadline;
  final DateTime applicationOpenDate;
  final VerificationStatus verificationStatus;
  final DateTime? lastVerifiedAt;
  final String officialSourceUrl;
  final String applicationUrl;
  final List<String> eligibleNationalities;
  final List<String> studyLevels;
  final List<String> fieldsOfStudy;
  final String summary;
  final List<String> benefits;
  final List<String> eligibilityRequirements;
  final List<String> requiredDocuments;
  final List<String> applicationProcedure;
  final List<String> languageRequirements;
  final int? minimumAge;
  final int? maximumAge;
  final double? workExperienceYearsRequired;
  final String contactInformation;
  final int? availablePositions;
  final DeliveryFormat deliveryFormat;
  final double? applicationFee;

  bool get isOpen => deadline.isAfter(DateTime.now());
  bool get isVerified => verificationStatus == VerificationStatus.verified;

  Opportunity copyWith({
    String? id,
    VerificationStatus? verificationStatus,
    DateTime? lastVerifiedAt,
    bool clearLastVerifiedAt = false,
  }) => Opportunity(
    id: id ?? this.id,
    title: title,
    provider: provider,
    hostInstitution: hostInstitution,
    hostCountry: hostCountry,
    type: type,
    funding: funding,
    deadline: deadline,
    applicationOpenDate: applicationOpenDate,
    verificationStatus: verificationStatus ?? this.verificationStatus,
    lastVerifiedAt: clearLastVerifiedAt
        ? null
        : lastVerifiedAt ?? this.lastVerifiedAt,
    officialSourceUrl: officialSourceUrl,
    applicationUrl: applicationUrl,
    eligibleNationalities: eligibleNationalities,
    studyLevels: studyLevels,
    fieldsOfStudy: fieldsOfStudy,
    summary: summary,
    benefits: benefits,
    eligibilityRequirements: eligibilityRequirements,
    requiredDocuments: requiredDocuments,
    applicationProcedure: applicationProcedure,
    languageRequirements: languageRequirements,
    minimumAge: minimumAge,
    maximumAge: maximumAge,
    workExperienceYearsRequired: workExperienceYearsRequired,
    contactInformation: contactInformation,
    availablePositions: availablePositions,
    deliveryFormat: deliveryFormat,
    applicationFee: applicationFee,
  );

  String get typeLabel => switch (type) {
    OpportunityType.scholarship => 'Scholarship',
    OpportunityType.fellowship => 'Fellowship',
    OpportunityType.internship => 'Internship',
    OpportunityType.conference => 'Conference',
    OpportunityType.summit => 'Summit',
    OpportunityType.webinar => 'Webinar',
    OpportunityType.exchangeProgram => 'Exchange program',
    OpportunityType.researchGrant => 'Research grant',
    OpportunityType.competition => 'Competition',
    OpportunityType.training => 'Training',
    OpportunityType.volunteering => 'Volunteering',
    OpportunityType.youthProgram => 'Youth program',
    OpportunityType.onlineCourse => 'Online course',
    OpportunityType.fundedEvent => 'Funded event',
    OpportunityType.grant => 'Grant',
    OpportunityType.job => 'Job',
  };

  String get fundingLabel => switch (funding) {
    FundingType.fullyFunded => 'Fully funded',
    FundingType.partiallyFunded => 'Partially funded',
    FundingType.selfFunded => 'Self funded',
  };

  String get deliveryLabel => switch (deliveryFormat) {
    DeliveryFormat.online => 'Online',
    DeliveryFormat.physical => 'In person',
    DeliveryFormat.hybrid => 'Hybrid',
  };

  String get verificationLabel => switch (verificationStatus) {
    VerificationStatus.pending => 'Pending verification',
    VerificationStatus.verified => 'Verified',
    VerificationStatus.verificationExpired => 'Verification expired',
    VerificationStatus.incomplete => 'Information incomplete',
    VerificationStatus.suspicious => 'Suspicious',
    VerificationStatus.rejected => 'Rejected',
    VerificationStatus.expired => 'Expired',
    VerificationStatus.archived => 'Archived',
  };
}
