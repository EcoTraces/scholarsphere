/// Mirrors scholarsphere_backend/app/models/testimonial.py and
/// app/schemas/testimonial.py exactly - the wire values below (e.g.
/// `awarded`, `first_name_last_initial`) are the backend's own enum
/// string values, never re-invented client-side.
library;

enum TestimonialOutcome {
  applied,
  shortlisted,
  interviewed,
  selected,
  awarded,
  admitted,
  funded,
  other;

  static TestimonialOutcome fromWire(String value) => values.firstWhere(
    (item) => item.wire == value,
    orElse: () => TestimonialOutcome.other,
  );

  String get wire => name;

  String get label => switch (this) {
    TestimonialOutcome.applied => 'Applied',
    TestimonialOutcome.shortlisted => 'Shortlisted',
    TestimonialOutcome.interviewed => 'Interviewed',
    TestimonialOutcome.selected => 'Selected',
    TestimonialOutcome.awarded => 'Awarded',
    TestimonialOutcome.admitted => 'Admitted',
    TestimonialOutcome.funded => 'Funded',
    TestimonialOutcome.other => 'Other outcome',
  };
}

enum TestimonialStatus {
  draft,
  submitted,
  underReview,
  changesRequested,
  approved,
  rejected,
  withdrawn;

  static TestimonialStatus fromWire(String value) => switch (value) {
    'draft' => TestimonialStatus.draft,
    'submitted' => TestimonialStatus.submitted,
    'under_review' => TestimonialStatus.underReview,
    'changes_requested' => TestimonialStatus.changesRequested,
    'approved' => TestimonialStatus.approved,
    'rejected' => TestimonialStatus.rejected,
    'withdrawn' => TestimonialStatus.withdrawn,
    _ => TestimonialStatus.draft,
  };

  String get label => switch (this) {
    TestimonialStatus.draft => 'Draft',
    TestimonialStatus.submitted => 'Submitted',
    TestimonialStatus.underReview => 'Under review',
    TestimonialStatus.changesRequested => 'Changes requested',
    TestimonialStatus.approved => 'Published',
    TestimonialStatus.rejected => 'Not approved',
    TestimonialStatus.withdrawn => 'Withdrawn',
  };
}

enum TestimonialVerificationStatus {
  unverified,
  verified;

  static TestimonialVerificationStatus fromWire(String value) =>
      value == 'verified'
      ? TestimonialVerificationStatus.verified
      : TestimonialVerificationStatus.unverified;
}

enum TestimonialDisplayMode {
  fullName,
  firstNameLastInitial,
  anonymous;

  static TestimonialDisplayMode fromWire(String value) => switch (value) {
    'full_name' => TestimonialDisplayMode.fullName,
    'anonymous' => TestimonialDisplayMode.anonymous,
    _ => TestimonialDisplayMode.firstNameLastInitial,
  };

  String get wire => switch (this) {
    TestimonialDisplayMode.fullName => 'full_name',
    TestimonialDisplayMode.firstNameLastInitial => 'first_name_last_initial',
    TestimonialDisplayMode.anonymous => 'anonymous',
  };

  String get label => switch (this) {
    TestimonialDisplayMode.fullName => 'Full name',
    TestimonialDisplayMode.firstNameLastInitial => 'First name + last initial',
    TestimonialDisplayMode.anonymous => 'Anonymous',
  };
}

enum TestimonialReactionType {
  helpful,
  inspiring,
  useful;

  String get wire => name;

  String get label => switch (this) {
    TestimonialReactionType.helpful => 'Helpful',
    TestimonialReactionType.inspiring => 'Inspiring',
    TestimonialReactionType.useful => 'Useful',
  };
}

/// A closed vocabulary matching KNOWN_FEATURES in
/// app/schemas/testimonial.py - the submission form only lets applicants
/// pick from this list, so "features used" badges are always meaningful.
const List<String> knownTestimonialFeatures = [
  'opportunity_discovery',
  'eligibility_matching',
  'application_preparation',
  'cv_builder',
  'document_management',
  'deadline_tracking',
  'guidance_plans',
  'ai_application_assistant',
  'calendar_sync',
  'notifications',
];

String featureLabel(String key) => switch (key) {
  'opportunity_discovery' => 'Opportunity Discovery',
  'eligibility_matching' => 'Eligibility Matching',
  'application_preparation' => 'Application Preparation',
  'cv_builder' => 'CV Builder',
  'document_management' => 'Document Management',
  'deadline_tracking' => 'Deadline Tracking',
  'guidance_plans' => 'Guidance Plans',
  'ai_application_assistant' => 'AI Application Assistant',
  'calendar_sync' => 'Calendar Sync',
  'notifications' => 'Notifications',
  _ => key,
};

/// Card-shaped view for list/search/featured/related-stories surfaces -
/// mirrors TestimonialSummaryRead. Never carries the real name, evidence,
/// or any other field the owner might have chosen to withhold.
class SuccessStorySummary {
  const SuccessStorySummary({
    required this.id,
    required this.slug,
    required this.displayName,
    required this.photoStoragePath,
    required this.country,
    required this.university,
    required this.program,
    required this.degreeLevel,
    required this.fieldOfStudy,
    required this.opportunityName,
    required this.opportunityProvider,
    required this.opportunityType,
    required this.outcome,
    required this.successYear,
    required this.verificationStatus,
    required this.featured,
    required this.badges,
    required this.excerpt,
    required this.featuresUsed,
    required this.helpfulCount,
    required this.inspiringCount,
    required this.usefulCount,
    required this.createdAt,
  });

  final String id;
  final String slug;
  final String displayName;
  final String? photoStoragePath;
  final String? country;
  final String? university;
  final String? program;
  final String? degreeLevel;
  final String? fieldOfStudy;
  final String opportunityName;
  final String opportunityProvider;
  final String opportunityType;
  final TestimonialOutcome outcome;
  final int? successYear;
  final TestimonialVerificationStatus verificationStatus;
  final bool featured;
  final List<String> badges;
  final String excerpt;
  final List<String> featuresUsed;
  final int helpfulCount;
  final int inspiringCount;
  final int usefulCount;
  final DateTime createdAt;

  bool get isVerified =>
      verificationStatus == TestimonialVerificationStatus.verified;
}

class SuccessStoryDetail {
  const SuccessStoryDetail({
    required this.id,
    required this.slug,
    required this.displayName,
    required this.photoStoragePath,
    required this.country,
    required this.university,
    required this.program,
    required this.degreeLevel,
    required this.fieldOfStudy,
    required this.opportunityId,
    required this.opportunityName,
    required this.opportunityProvider,
    required this.opportunityType,
    required this.outcome,
    required this.successYear,
    required this.challenge,
    required this.discoveryStory,
    required this.preparationStory,
    required this.scholarsphereHelp,
    required this.outcomeNarrative,
    required this.impact,
    required this.advice,
    required this.featuresUsed,
    required this.verificationStatus,
    required this.featured,
    required this.badges,
    required this.helpfulCount,
    required this.inspiringCount,
    required this.usefulCount,
    required this.viewCount,
    required this.createdAt,
  });

  final String id;
  final String slug;
  final String displayName;
  final String? photoStoragePath;
  final String? country;
  final String? university;
  final String? program;
  final String? degreeLevel;
  final String? fieldOfStudy;
  final String? opportunityId;
  final String opportunityName;
  final String opportunityProvider;
  final String opportunityType;
  final TestimonialOutcome outcome;
  final int? successYear;
  final String? challenge;
  final String? discoveryStory;
  final String? preparationStory;
  final String? scholarsphereHelp;
  final String? outcomeNarrative;
  final String? impact;
  final String? advice;
  final List<String> featuresUsed;
  final TestimonialVerificationStatus verificationStatus;
  final bool featured;
  final List<String> badges;
  final int helpfulCount;
  final int inspiringCount;
  final int usefulCount;
  final int viewCount;
  final DateTime createdAt;

  bool get isVerified =>
      verificationStatus == TestimonialVerificationStatus.verified;
}

/// The owner's own view of a submission, at any status - always shows the
/// real fields they entered (mirrors TestimonialOwnRead).
class MyTestimonial {
  const MyTestimonial({
    required this.id,
    required this.slug,
    required this.status,
    required this.verificationStatus,
    required this.featured,
    required this.opportunityId,
    required this.opportunityName,
    required this.opportunityProvider,
    required this.opportunityType,
    required this.country,
    required this.degreeLevel,
    required this.fieldOfStudy,
    required this.successYear,
    required this.outcome,
    required this.challenge,
    required this.discoveryStory,
    required this.preparationStory,
    required this.scholarsphereHelp,
    required this.outcomeNarrative,
    required this.impact,
    required this.advice,
    required this.featuresUsed,
    required this.fullName,
    required this.university,
    required this.program,
    required this.photoStoragePath,
    required this.displayMode,
    required this.showUniversity,
    required this.showCountry,
    required this.showProgram,
    required this.showPhoto,
    required this.evidenceStoragePaths,
    required this.rejectionReason,
    required this.submittedAt,
    required this.approvedAt,
    required this.verifiedAt,
    required this.withdrawnAt,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String slug;
  final TestimonialStatus status;
  final TestimonialVerificationStatus verificationStatus;
  final bool featured;
  final String? opportunityId;
  final String opportunityName;
  final String opportunityProvider;
  final String opportunityType;
  final String? country;
  final String? degreeLevel;
  final String? fieldOfStudy;
  final int? successYear;
  final TestimonialOutcome outcome;
  final String? challenge;
  final String? discoveryStory;
  final String? preparationStory;
  final String? scholarsphereHelp;
  final String? outcomeNarrative;
  final String? impact;
  final String? advice;
  final List<String> featuresUsed;
  final String fullName;
  final String? university;
  final String? program;
  final String? photoStoragePath;
  final TestimonialDisplayMode displayMode;
  final bool showUniversity;
  final bool showCountry;
  final bool showProgram;
  final bool showPhoto;
  final List<String> evidenceStoragePaths;
  final String? rejectionReason;
  final DateTime? submittedAt;
  final DateTime? approvedAt;
  final DateTime? verifiedAt;
  final DateTime? withdrawnAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  bool get isEditable =>
      status == TestimonialStatus.draft ||
      status == TestimonialStatus.changesRequested;
  bool get isWithdrawable =>
      status == TestimonialStatus.submitted ||
      status == TestimonialStatus.underReview ||
      status == TestimonialStatus.approved;
}

class AdminTestimonial extends MyTestimonial {
  const AdminTestimonial({
    required super.id,
    required super.slug,
    required super.status,
    required super.verificationStatus,
    required super.featured,
    required super.opportunityId,
    required super.opportunityName,
    required super.opportunityProvider,
    required super.opportunityType,
    required super.country,
    required super.degreeLevel,
    required super.fieldOfStudy,
    required super.successYear,
    required super.outcome,
    required super.challenge,
    required super.discoveryStory,
    required super.preparationStory,
    required super.scholarsphereHelp,
    required super.outcomeNarrative,
    required super.impact,
    required super.advice,
    required super.featuresUsed,
    required super.fullName,
    required super.university,
    required super.program,
    required super.photoStoragePath,
    required super.displayMode,
    required super.showUniversity,
    required super.showCountry,
    required super.showProgram,
    required super.showPhoto,
    required super.evidenceStoragePaths,
    required super.rejectionReason,
    required super.submittedAt,
    required super.approvedAt,
    required super.verifiedAt,
    required super.withdrawnAt,
    required super.createdAt,
    required super.updatedAt,
    required this.userId,
    required this.internalNotes,
    required this.verifiedBy,
    required this.verificationMethod,
    required this.lastModeratorId,
    required this.rejectedAt,
  });

  final String userId;
  final String? internalNotes;
  final String? verifiedBy;
  final String? verificationMethod;
  final String? lastModeratorId;
  final DateTime? rejectedAt;
}

class TestimonialModerationHistoryItem {
  const TestimonialModerationHistoryItem({
    required this.id,
    required this.previousStatus,
    required this.newStatus,
    required this.actorId,
    required this.notes,
    required this.createdAt,
  });

  final String id;
  final String previousStatus;
  final String newStatus;
  final String actorId;
  final String notes;
  final DateTime createdAt;
}

class SuccessStoryPage {
  const SuccessStoryPage({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  final List<SuccessStorySummary> items;
  final int total;
  final int page;
  final int pageSize;

  bool get hasMore => page * pageSize < total;
}

class AdminTestimonialPage {
  const AdminTestimonialPage({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  final List<AdminTestimonial> items;
  final int total;
  final int page;
  final int pageSize;

  bool get hasMore => page * pageSize < total;
}

/// Every field is nullable - a `null` count means "hide this statistic",
/// never a fabricated zero (mirrors TestimonialStatsRead's own contract).
class TestimonialStats {
  const TestimonialStats({
    required this.totalStories,
    required this.verifiedStories,
    required this.countriesRepresented,
    required this.opportunityTypesRepresented,
    required this.fieldsOfStudyRepresented,
  });

  final int? totalStories;
  final int? verifiedStories;
  final int? countriesRepresented;
  final int? opportunityTypesRepresented;
  final int? fieldsOfStudyRepresented;

  bool get hasAnyStat =>
      totalStories != null ||
      verifiedStories != null ||
      countriesRepresented != null ||
      opportunityTypesRepresented != null ||
      fieldsOfStudyRepresented != null;
}

/// The full submission-wizard payload - steps 1-5 of the form map
/// directly onto these fields, mirroring TestimonialDraftRequest.
class TestimonialDraftInput {
  const TestimonialDraftInput({
    this.opportunityId,
    required this.opportunityName,
    required this.opportunityProvider,
    required this.opportunityType,
    this.country,
    this.degreeLevel,
    this.fieldOfStudy,
    this.successYear,
    required this.outcome,
    this.challenge,
    this.discoveryStory,
    this.preparationStory,
    this.scholarsphereHelp,
    this.outcomeNarrative,
    this.impact,
    this.advice,
    this.featuresUsed = const [],
    required this.fullName,
    this.university,
    this.program,
    this.photoStoragePath,
    this.displayMode = TestimonialDisplayMode.firstNameLastInitial,
    this.showUniversity = true,
    this.showCountry = true,
    this.showProgram = true,
    this.showPhoto = false,
    this.evidenceStoragePaths = const [],
  });

  final String? opportunityId;
  final String opportunityName;
  final String opportunityProvider;
  final String opportunityType;
  final String? country;
  final String? degreeLevel;
  final String? fieldOfStudy;
  final int? successYear;
  final TestimonialOutcome outcome;
  final String? challenge;
  final String? discoveryStory;
  final String? preparationStory;
  final String? scholarsphereHelp;
  final String? outcomeNarrative;
  final String? impact;
  final String? advice;
  final List<String> featuresUsed;
  final String fullName;
  final String? university;
  final String? program;
  final String? photoStoragePath;
  final TestimonialDisplayMode displayMode;
  final bool showUniversity;
  final bool showCountry;
  final bool showProgram;
  final bool showPhoto;
  final List<String> evidenceStoragePaths;

  Map<String, dynamic> toJson() => {
    'opportunity': {
      if (opportunityId != null) 'opportunity_id': opportunityId,
      'opportunity_name': opportunityName,
      'opportunity_provider': opportunityProvider,
      'opportunity_type': opportunityType,
      'country': country,
      'degree_level': degreeLevel,
      'field_of_study': fieldOfStudy,
      'success_year': successYear,
      'outcome': outcome.wire,
    },
    'experience': {
      'challenge': challenge,
      'discovery_story': discoveryStory,
      'preparation_story': preparationStory,
      'scholarsphere_help': scholarsphereHelp,
      'outcome_narrative': outcomeNarrative,
      'impact': impact,
      'advice': advice,
      'features_used': featuresUsed,
    },
    'profile': {
      'full_name': fullName,
      'university': university,
      'program': program,
      'photo_storage_path': photoStoragePath,
    },
    'privacy': {
      'display_mode': displayMode.wire,
      'show_university': showUniversity,
      'show_country': showCountry,
      'show_program': showProgram,
      'show_photo': showPhoto,
    },
    'evidence_storage_paths': evidenceStoragePaths,
  };

  TestimonialDraftInput copyWith({
    String? opportunityId,
    bool clearOpportunityId = false,
    String? opportunityName,
    String? opportunityProvider,
    String? opportunityType,
    String? country,
    String? degreeLevel,
    String? fieldOfStudy,
    int? successYear,
    TestimonialOutcome? outcome,
    String? challenge,
    String? discoveryStory,
    String? preparationStory,
    String? scholarsphereHelp,
    String? outcomeNarrative,
    String? impact,
    String? advice,
    List<String>? featuresUsed,
    String? fullName,
    String? university,
    String? program,
    String? photoStoragePath,
    TestimonialDisplayMode? displayMode,
    bool? showUniversity,
    bool? showCountry,
    bool? showProgram,
    bool? showPhoto,
    List<String>? evidenceStoragePaths,
  }) => TestimonialDraftInput(
    opportunityId: clearOpportunityId
        ? null
        : (opportunityId ?? this.opportunityId),
    opportunityName: opportunityName ?? this.opportunityName,
    opportunityProvider: opportunityProvider ?? this.opportunityProvider,
    opportunityType: opportunityType ?? this.opportunityType,
    country: country ?? this.country,
    degreeLevel: degreeLevel ?? this.degreeLevel,
    fieldOfStudy: fieldOfStudy ?? this.fieldOfStudy,
    successYear: successYear ?? this.successYear,
    outcome: outcome ?? this.outcome,
    challenge: challenge ?? this.challenge,
    discoveryStory: discoveryStory ?? this.discoveryStory,
    preparationStory: preparationStory ?? this.preparationStory,
    scholarsphereHelp: scholarsphereHelp ?? this.scholarsphereHelp,
    outcomeNarrative: outcomeNarrative ?? this.outcomeNarrative,
    impact: impact ?? this.impact,
    advice: advice ?? this.advice,
    featuresUsed: featuresUsed ?? this.featuresUsed,
    fullName: fullName ?? this.fullName,
    university: university ?? this.university,
    program: program ?? this.program,
    photoStoragePath: photoStoragePath ?? this.photoStoragePath,
    displayMode: displayMode ?? this.displayMode,
    showUniversity: showUniversity ?? this.showUniversity,
    showCountry: showCountry ?? this.showCountry,
    showProgram: showProgram ?? this.showProgram,
    showPhoto: showPhoto ?? this.showPhoto,
    evidenceStoragePaths: evidenceStoragePaths ?? this.evidenceStoragePaths,
  );

  static const empty = TestimonialDraftInput(
    opportunityName: '',
    opportunityProvider: '',
    opportunityType: 'scholarship',
    outcome: TestimonialOutcome.awarded,
    fullName: '',
  );
}
