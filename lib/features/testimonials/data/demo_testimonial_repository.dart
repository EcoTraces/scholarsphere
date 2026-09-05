import '../domain/testimonial.dart';
import '../domain/testimonial_repository.dart';

/// In-memory, development-only sample data - never talks to the real
/// backend. Every seeded record is prefixed "DEMO —" in every
/// user-visible field (matching this project's standing rule against
/// ever presenting fabricated success stories as genuine, Section on
/// test data in the Success Stories feature spec), so it can never be
/// mistaken for a real applicant's story if it were ever shown by
/// mistake. Screens should reach this repository only in local
/// development/demo builds, never in a build pointed at production -
/// the same convention [DemoPremiumRepository] already established.
class DemoTestimonialRepository implements TestimonialRepository {
  DemoTestimonialRepository() {
    _seed();
  }

  final List<_DemoRecord> _records = [];
  final Map<String, TestimonialReactionType> _myReactions = {};
  int _counter = 0;

  void _seed() {
    _records.addAll([
      _DemoRecord(
        id: 'demo-testimonial-1',
        slug: 'demo-aminata-commonwealth-2026',
        userId: 'demo-user-1',
        status: TestimonialStatus.approved,
        verificationStatus: TestimonialVerificationStatus.verified,
        featured: true,
        opportunityName: 'DEMO — Commonwealth Shared Scholarship',
        opportunityProvider: 'DEMO — Commonwealth Scholarship Commission',
        opportunityType: 'scholarship',
        country: 'DEMO — Sierra Leone',
        degreeLevel: 'Masters',
        fieldOfStudy: 'Public Health',
        successYear: 2026,
        outcome: TestimonialOutcome.awarded,
        challenge:
            'DEMO — I could not find funded master\'s programmes that matched my background.',
        discoveryStory:
            'DEMO — Found the opportunity through the ScholarSphere discovery feed.',
        preparationStory:
            'DEMO — Used the CV builder and requirement checklist to prepare every document.',
        scholarsphereHelp:
            'DEMO — Eligibility matching saved weeks of manual research.',
        outcomeNarrative:
            'DEMO — Awarded the scholarship and started the programme in September.',
        impact:
            'DEMO — This sample story shows how the impact question renders.',
        advice:
            'DEMO — This sample story shows how the advice question renders.',
        featuresUsed: const ['opportunity_discovery', 'cv_builder'],
        fullName: 'DEMO — Example Applicant',
        university: 'DEMO — Sample University',
        program: 'DEMO — MSc Public Health',
        displayMode: TestimonialDisplayMode.firstNameLastInitial,
      ),
      _DemoRecord(
        id: 'demo-testimonial-2',
        slug: 'demo-second-story-2025',
        userId: 'demo-user-2',
        status: TestimonialStatus.approved,
        verificationStatus: TestimonialVerificationStatus.unverified,
        featured: false,
        opportunityName: 'DEMO — Sample Graduate Fellowship',
        opportunityProvider: 'DEMO — Sample Foundation',
        opportunityType: 'fellowship',
        country: 'DEMO — Ghana',
        degreeLevel: 'PhD',
        fieldOfStudy: 'Environmental Science',
        successYear: 2025,
        outcome: TestimonialOutcome.funded,
        challenge: 'DEMO — Sample challenge text for preview purposes only.',
        discoveryStory:
            'DEMO — Sample discovery text for preview purposes only.',
        preparationStory:
            'DEMO — Sample preparation text for preview purposes only.',
        scholarsphereHelp: 'DEMO — Sample help text for preview purposes only.',
        outcomeNarrative:
            'DEMO — Sample outcome text for preview purposes only.',
        impact: 'DEMO — Sample impact text for preview purposes only.',
        advice: 'DEMO — Sample advice text for preview purposes only.',
        featuresUsed: const ['guidance_plans', 'deadline_tracking'],
        fullName: 'DEMO — Second Example',
        university: null,
        program: null,
        displayMode: TestimonialDisplayMode.anonymous,
        showUniversity: false,
        showCountry: true,
        showProgram: false,
        showPhoto: false,
      ),
    ]);
  }

  String _nextId() => 'demo-testimonial-${_records.length + (++_counter) + 10}';

  @override
  Future<SuccessStoryPage> listSuccessStories(
    SuccessStoryFilters filters, {
    int page = 1,
    int pageSize = 25,
  }) async {
    final visible = _records
        .where((record) => record.status == TestimonialStatus.approved)
        .where((record) {
          if (filters.opportunityType != null &&
              record.opportunityType != filters.opportunityType) {
            return false;
          }
          if (filters.country != null && record.country != filters.country) {
            return false;
          }
          if (filters.fieldOfStudy != null &&
              record.fieldOfStudy != filters.fieldOfStudy) {
            return false;
          }
          if (filters.degreeLevel != null &&
              record.degreeLevel != filters.degreeLevel) {
            return false;
          }
          if (filters.successYear != null &&
              record.successYear != filters.successYear) {
            return false;
          }
          if (filters.verifiedOnly &&
              record.verificationStatus !=
                  TestimonialVerificationStatus.verified) {
            return false;
          }
          if (filters.featuredOnly && !record.featured) return false;
          if (filters.keyword != null && filters.keyword!.isNotEmpty) {
            final needle = filters.keyword!.toLowerCase();
            if (!record.opportunityName.toLowerCase().contains(needle) &&
                !(record.outcomeNarrative ?? '').toLowerCase().contains(
                  needle,
                )) {
              return false;
            }
          }
          return true;
        })
        .toList();
    if (filters.sort == 'featured') {
      visible.sort((a, b) => (b.featured ? 1 : 0) - (a.featured ? 1 : 0));
    }
    final items = visible.map(_toSummary).toList();
    return SuccessStoryPage(
      items: items,
      total: items.length,
      page: page,
      pageSize: pageSize,
    );
  }

  @override
  Future<TestimonialStats> getStats() async {
    final approved = _records.where(
      (record) => record.status == TestimonialStatus.approved,
    );
    if (approved.isEmpty) {
      return const TestimonialStats(
        totalStories: null,
        verifiedStories: null,
        countriesRepresented: null,
        opportunityTypesRepresented: null,
        fieldsOfStudyRepresented: null,
      );
    }
    return TestimonialStats(
      totalStories: approved.length,
      verifiedStories: approved
          .where(
            (record) =>
                record.verificationStatus ==
                TestimonialVerificationStatus.verified,
          )
          .length,
      countriesRepresented: approved
          .map((record) => record.country)
          .whereType<String>()
          .toSet()
          .length,
      opportunityTypesRepresented: approved
          .map((record) => record.opportunityType)
          .toSet()
          .length,
      fieldsOfStudyRepresented: approved
          .map((record) => record.fieldOfStudy)
          .whereType<String>()
          .toSet()
          .length,
    );
  }

  @override
  Future<SuccessStoryDetail> getStory(String slug) async {
    final record = _findBySlug(slug);
    record.viewCount += 1;
    return _toDetail(record);
  }

  @override
  Future<List<SuccessStorySummary>> getRelatedStories(
    String slug, {
    int limit = 4,
  }) async {
    final record = _findBySlug(slug);
    return _records
        .where(
          (item) =>
              item.id != record.id &&
              item.status == TestimonialStatus.approved &&
              item.opportunityType == record.opportunityType,
        )
        .take(limit)
        .map(_toSummary)
        .toList();
  }

  @override
  Future<SuccessStoryDetail> react(
    String slug,
    TestimonialReactionType type,
  ) async {
    final record = _findBySlug(slug);
    final previous = _myReactions['demo-current-user:${record.id}'];
    if (previous != null) {
      record.reactionCount(previous, -1);
    }
    _myReactions['demo-current-user:${record.id}'] = type;
    record.reactionCount(type, 1);
    return _toDetail(record);
  }

  @override
  Future<SuccessStoryDetail> removeReaction(String slug) async {
    final record = _findBySlug(slug);
    final previous = _myReactions.remove('demo-current-user:${record.id}');
    if (previous != null) record.reactionCount(previous, -1);
    return _toDetail(record);
  }

  @override
  Future<List<MyTestimonial>> listMine() async => _records
      .where((record) => record.userId == 'demo-current-user')
      .map(_toMine)
      .toList();

  @override
  Future<MyTestimonial> getMine(String testimonialId) async =>
      _toMine(_findById(testimonialId));

  @override
  Future<MyTestimonial> saveDraft(
    TestimonialDraftInput input, {
    String? id,
  }) async {
    _DemoRecord record;
    if (id == null) {
      record = _DemoRecord(
        id: _nextId(),
        slug: 'demo-${DateTime.now().millisecondsSinceEpoch}',
        userId: 'demo-current-user',
        status: TestimonialStatus.draft,
        verificationStatus: TestimonialVerificationStatus.unverified,
        featured: false,
        opportunityName: '',
        opportunityProvider: '',
        opportunityType: '',
        country: null,
        degreeLevel: null,
        fieldOfStudy: null,
        successYear: null,
        outcome: input.outcome,
        challenge: null,
        discoveryStory: null,
        preparationStory: null,
        scholarsphereHelp: null,
        outcomeNarrative: null,
        impact: null,
        advice: null,
        featuresUsed: const [],
        fullName: '',
        university: null,
        program: null,
        displayMode: TestimonialDisplayMode.firstNameLastInitial,
      );
      _records.add(record);
    } else {
      record = _findById(id);
      if (record.status != TestimonialStatus.draft &&
          record.status != TestimonialStatus.changesRequested) {
        throw StateError('This story is no longer editable.');
      }
    }
    record
      ..opportunityName = input.opportunityName
      ..opportunityProvider = input.opportunityProvider
      ..opportunityType = input.opportunityType
      ..country = input.country
      ..degreeLevel = input.degreeLevel
      ..fieldOfStudy = input.fieldOfStudy
      ..successYear = input.successYear
      ..outcome = input.outcome
      ..challenge = input.challenge
      ..discoveryStory = input.discoveryStory
      ..preparationStory = input.preparationStory
      ..scholarsphereHelp = input.scholarsphereHelp
      ..outcomeNarrative = input.outcomeNarrative
      ..impact = input.impact
      ..advice = input.advice
      ..featuresUsed = input.featuresUsed
      ..fullName = input.fullName
      ..university = input.university
      ..program = input.program
      ..photoStoragePath = input.photoStoragePath
      ..displayMode = input.displayMode
      ..showUniversity = input.showUniversity
      ..showCountry = input.showCountry
      ..showProgram = input.showProgram
      ..showPhoto = input.showPhoto
      ..evidenceStoragePaths = input.evidenceStoragePaths;
    if (record.status == TestimonialStatus.changesRequested) {
      record.status = TestimonialStatus.draft;
    }
    return _toMine(record);
  }

  @override
  Future<MyTestimonial> submit(String testimonialId) async {
    final record = _findById(testimonialId);
    record.status = TestimonialStatus.submitted;
    record.submittedAt = DateTime.now();
    return _toMine(record);
  }

  @override
  Future<MyTestimonial> withdraw(String testimonialId) async {
    final record = _findById(testimonialId);
    record.status = TestimonialStatus.withdrawn;
    record.withdrawnAt = DateTime.now();
    return _toMine(record);
  }

  @override
  Future<String> getMyEvidenceUrl(String testimonialId, String path) async =>
      'https://example.invalid/demo-evidence-preview';

  @override
  Future<AdminTestimonialPage> listForModeration(
    AdminTestimonialFilters filters, {
    int page = 1,
    int pageSize = 25,
  }) async {
    final filtered = _records.where((record) {
      if (filters.status != null && record.status != filters.status) {
        return false;
      }
      return true;
    }).toList();
    final items = filtered.map(_toAdmin).toList();
    return AdminTestimonialPage(
      items: items,
      total: items.length,
      page: page,
      pageSize: pageSize,
    );
  }

  @override
  Future<AdminTestimonial> getForModeration(String testimonialId) async =>
      _toAdmin(_findById(testimonialId));

  @override
  Future<List<TestimonialModerationHistoryItem>> getModerationHistory(
    String testimonialId,
  ) async => const [];

  @override
  Future<AdminTestimonial> markUnderReview(String testimonialId) async {
    final record = _findById(testimonialId);
    record.status = TestimonialStatus.underReview;
    return _toAdmin(record);
  }

  @override
  Future<AdminTestimonial> approve(String testimonialId, String notes) async {
    final record = _findById(testimonialId);
    record.status = TestimonialStatus.approved;
    record.approvedAt = DateTime.now();
    return _toAdmin(record);
  }

  @override
  Future<AdminTestimonial> reject(String testimonialId, String reason) async {
    final record = _findById(testimonialId);
    record.status = TestimonialStatus.rejected;
    record.rejectionReason = reason;
    return _toAdmin(record);
  }

  @override
  Future<AdminTestimonial> requestChanges(
    String testimonialId,
    String reason,
  ) async {
    final record = _findById(testimonialId);
    record.status = TestimonialStatus.changesRequested;
    record.rejectionReason = reason;
    return _toAdmin(record);
  }

  @override
  Future<AdminTestimonial> verify(
    String testimonialId,
    String verificationMethod,
    String? notes,
  ) async {
    final record = _findById(testimonialId);
    record.verificationStatus = TestimonialVerificationStatus.verified;
    record.verifiedAt = DateTime.now();
    record.verificationMethod = verificationMethod;
    record.verifiedBy = 'demo-moderator';
    return _toAdmin(record);
  }

  @override
  Future<AdminTestimonial> feature(String testimonialId) async {
    final record = _findById(testimonialId);
    if (record.status != TestimonialStatus.approved) {
      throw StateError('Only approved stories can be featured.');
    }
    record.featured = true;
    return _toAdmin(record);
  }

  @override
  Future<AdminTestimonial> unfeature(String testimonialId) async {
    final record = _findById(testimonialId);
    record.featured = false;
    return _toAdmin(record);
  }

  @override
  Future<AdminTestimonial> archive(String testimonialId, String reason) async {
    final record = _findById(testimonialId);
    record.status = TestimonialStatus.withdrawn;
    record.withdrawnAt = DateTime.now();
    return _toAdmin(record);
  }

  @override
  Future<AdminTestimonial> setInternalNotes(
    String testimonialId,
    String notes,
  ) async {
    final record = _findById(testimonialId);
    record.internalNotes = notes.isEmpty ? null : notes;
    return _toAdmin(record);
  }

  @override
  Future<String> getAdminEvidenceUrl(String testimonialId, String path) async =>
      'https://example.invalid/demo-evidence-preview';

  _DemoRecord _findById(String id) => _records.firstWhere(
    (record) => record.id == id,
    orElse: () => throw StateError('Not found: $id'),
  );

  _DemoRecord _findBySlug(String slug) => _records.firstWhere(
    (record) => record.slug == slug,
    orElse: () => throw StateError('Not found: $slug'),
  );

  SuccessStorySummary _toSummary(_DemoRecord record) => SuccessStorySummary(
    id: record.id,
    slug: record.slug,
    displayName: record.displayName,
    photoStoragePath: record.showPhoto ? record.photoStoragePath : null,
    country: record.showCountry ? record.country : null,
    university: record.showUniversity ? record.university : null,
    program: record.showProgram ? record.program : null,
    degreeLevel: record.degreeLevel,
    fieldOfStudy: record.fieldOfStudy,
    opportunityName: record.opportunityName,
    opportunityProvider: record.opportunityProvider,
    opportunityType: record.opportunityType,
    outcome: record.outcome,
    successYear: record.successYear,
    verificationStatus: record.verificationStatus,
    featured: record.featured,
    badges: record.badges,
    excerpt: (record.outcomeNarrative ?? '').length > 160
        ? '${(record.outcomeNarrative ?? '').substring(0, 157)}...'
        : (record.outcomeNarrative ?? ''),
    featuresUsed: record.featuresUsed,
    helpfulCount: record.helpfulCount,
    inspiringCount: record.inspiringCount,
    usefulCount: record.usefulCount,
    createdAt: record.createdAt,
  );

  SuccessStoryDetail _toDetail(_DemoRecord record) => SuccessStoryDetail(
    id: record.id,
    slug: record.slug,
    displayName: record.displayName,
    photoStoragePath: record.showPhoto ? record.photoStoragePath : null,
    country: record.showCountry ? record.country : null,
    university: record.showUniversity ? record.university : null,
    program: record.showProgram ? record.program : null,
    degreeLevel: record.degreeLevel,
    fieldOfStudy: record.fieldOfStudy,
    opportunityId: null,
    opportunityName: record.opportunityName,
    opportunityProvider: record.opportunityProvider,
    opportunityType: record.opportunityType,
    outcome: record.outcome,
    successYear: record.successYear,
    challenge: record.challenge,
    discoveryStory: record.discoveryStory,
    preparationStory: record.preparationStory,
    scholarsphereHelp: record.scholarsphereHelp,
    outcomeNarrative: record.outcomeNarrative,
    impact: record.impact,
    advice: record.advice,
    featuresUsed: record.featuresUsed,
    verificationStatus: record.verificationStatus,
    featured: record.featured,
    badges: record.badges,
    helpfulCount: record.helpfulCount,
    inspiringCount: record.inspiringCount,
    usefulCount: record.usefulCount,
    viewCount: record.viewCount,
    createdAt: record.createdAt,
  );

  MyTestimonial _toMine(_DemoRecord record) => MyTestimonial(
    id: record.id,
    slug: record.slug,
    status: record.status,
    verificationStatus: record.verificationStatus,
    featured: record.featured,
    opportunityId: null,
    opportunityName: record.opportunityName,
    opportunityProvider: record.opportunityProvider,
    opportunityType: record.opportunityType,
    country: record.country,
    degreeLevel: record.degreeLevel,
    fieldOfStudy: record.fieldOfStudy,
    successYear: record.successYear,
    outcome: record.outcome,
    challenge: record.challenge,
    discoveryStory: record.discoveryStory,
    preparationStory: record.preparationStory,
    scholarsphereHelp: record.scholarsphereHelp,
    outcomeNarrative: record.outcomeNarrative,
    impact: record.impact,
    advice: record.advice,
    featuresUsed: record.featuresUsed,
    fullName: record.fullName,
    university: record.university,
    program: record.program,
    photoStoragePath: record.photoStoragePath,
    displayMode: record.displayMode,
    showUniversity: record.showUniversity,
    showCountry: record.showCountry,
    showProgram: record.showProgram,
    showPhoto: record.showPhoto,
    evidenceStoragePaths: record.evidenceStoragePaths,
    rejectionReason: record.rejectionReason,
    submittedAt: record.submittedAt,
    approvedAt: record.approvedAt,
    verifiedAt: record.verifiedAt,
    withdrawnAt: record.withdrawnAt,
    createdAt: record.createdAt,
    updatedAt: record.createdAt,
  );

  AdminTestimonial _toAdmin(_DemoRecord record) {
    final mine = _toMine(record);
    return AdminTestimonial(
      id: mine.id,
      slug: mine.slug,
      status: mine.status,
      verificationStatus: mine.verificationStatus,
      featured: mine.featured,
      opportunityId: mine.opportunityId,
      opportunityName: mine.opportunityName,
      opportunityProvider: mine.opportunityProvider,
      opportunityType: mine.opportunityType,
      country: mine.country,
      degreeLevel: mine.degreeLevel,
      fieldOfStudy: mine.fieldOfStudy,
      successYear: mine.successYear,
      outcome: mine.outcome,
      challenge: mine.challenge,
      discoveryStory: mine.discoveryStory,
      preparationStory: mine.preparationStory,
      scholarsphereHelp: mine.scholarsphereHelp,
      outcomeNarrative: mine.outcomeNarrative,
      impact: mine.impact,
      advice: mine.advice,
      featuresUsed: mine.featuresUsed,
      fullName: mine.fullName,
      university: mine.university,
      program: mine.program,
      photoStoragePath: mine.photoStoragePath,
      displayMode: mine.displayMode,
      showUniversity: mine.showUniversity,
      showCountry: mine.showCountry,
      showProgram: mine.showProgram,
      showPhoto: mine.showPhoto,
      evidenceStoragePaths: mine.evidenceStoragePaths,
      rejectionReason: mine.rejectionReason,
      submittedAt: mine.submittedAt,
      approvedAt: mine.approvedAt,
      verifiedAt: mine.verifiedAt,
      withdrawnAt: mine.withdrawnAt,
      createdAt: mine.createdAt,
      updatedAt: mine.updatedAt,
      userId: record.userId,
      internalNotes: record.internalNotes,
      verifiedBy: record.verifiedBy,
      verificationMethod: record.verificationMethod,
      lastModeratorId: null,
      rejectedAt: null,
    );
  }
}

class _DemoRecord {
  _DemoRecord({
    required this.id,
    required this.slug,
    required this.userId,
    required this.status,
    required this.verificationStatus,
    required this.featured,
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
    required this.displayMode,
    this.showUniversity = true,
    this.showCountry = true,
    this.showProgram = true,
    this.showPhoto = false,
  }) : createdAt = DateTime.now();

  final String id;
  final String slug;
  final String userId;
  TestimonialStatus status;
  TestimonialVerificationStatus verificationStatus;
  bool featured;
  String opportunityName;
  String opportunityProvider;
  String opportunityType;
  String? country;
  String? degreeLevel;
  String? fieldOfStudy;
  int? successYear;
  TestimonialOutcome outcome;
  String? challenge;
  String? discoveryStory;
  String? preparationStory;
  String? scholarsphereHelp;
  String? outcomeNarrative;
  String? impact;
  String? advice;
  List<String> featuresUsed;
  String fullName;
  String? university;
  String? program;
  String? photoStoragePath;
  TestimonialDisplayMode displayMode;
  bool showUniversity;
  bool showCountry;
  bool showProgram;
  bool showPhoto;
  List<String> evidenceStoragePaths = const [];
  String? rejectionReason;
  String? verifiedBy;
  String? verificationMethod;
  String? internalNotes;
  DateTime? submittedAt;
  DateTime? approvedAt;
  DateTime? verifiedAt;
  DateTime? withdrawnAt;
  final DateTime createdAt;
  int viewCount = 0;
  int helpfulCount = 0;
  int inspiringCount = 0;
  int usefulCount = 0;

  String get displayName {
    final name = fullName.trim();
    if (displayMode == TestimonialDisplayMode.anonymous || name.isEmpty) {
      return 'Anonymous Applicant';
    }
    if (displayMode == TestimonialDisplayMode.fullName) return name;
    final parts = name.split(' ');
    if (parts.length == 1) return parts.first;
    return '${parts.first} ${parts.last[0]}.';
  }

  List<String> get badges {
    final result = <String>[];
    if (featured && status == TestimonialStatus.approved) {
      result.add('featured');
    }
    if (verificationStatus == TestimonialVerificationStatus.verified) {
      result.add('verified');
    } else if (status == TestimonialStatus.approved) {
      result.add('community');
    } else {
      result.add('under_review');
    }
    return result;
  }

  void reactionCount(TestimonialReactionType type, int delta) {
    switch (type) {
      case TestimonialReactionType.helpful:
        helpfulCount = (helpfulCount + delta).clamp(0, 1 << 30);
      case TestimonialReactionType.inspiring:
        inspiringCount = (inspiringCount + delta).clamp(0, 1 << 30);
      case TestimonialReactionType.useful:
        usefulCount = (usefulCount + delta).clamp(0, 1 << 30);
    }
  }
}
