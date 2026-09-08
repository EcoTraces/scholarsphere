import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../opportunities/domain/opportunity.dart';
import '../../security/domain/security_backend_contracts.dart';
import '../domain/verification_repository.dart';
import '../domain/verification_review.dart';

const _notSpecified = 'Not specified by source';

/// A single-officer, timestamped note attached to an opportunity as
/// evidence, without changing its verification status.
class LiveVerificationNote {
  const LiveVerificationNote({required this.opportunityId, required this.note});

  final String opportunityId;
  final String note;
}

/// The live backend's actual verification-review state: one officer,
/// one decision, a four-item checklist. Deliberately not the richer
/// [VerificationReview] domain type, which models a two-person-approval
/// workflow (assignment, 13-item checklist, second approver, appeals,
/// conflict resolution) that the live backend does not implement - see
/// [ApiVerificationRepository]'s class doc comment.
class LiveVerificationReview {
  const LiveVerificationReview({
    required this.opportunityId,
    required this.verificationOfficerId,
    required this.sourceChecked,
    required this.applicationLinkChecked,
    required this.deadlineChecked,
    required this.duplicateChecked,
    required this.decision,
    required this.notes,
    required this.verifiedAt,
    required this.updatedAt,
  });

  factory LiveVerificationReview.fromJson(Map<String, dynamic> json) =>
      LiveVerificationReview(
        opportunityId: json['opportunity_id'] as String,
        verificationOfficerId: json['verification_officer_id'] as String?,
        sourceChecked: json['source_checked'] as bool,
        applicationLinkChecked: json['application_link_checked'] as bool,
        deadlineChecked: json['deadline_checked'] as bool,
        duplicateChecked: json['duplicate_checked'] as bool,
        decision: json['decision'] as String,
        notes: json['notes'] as String?,
        verifiedAt: _dateTime(json['verified_at']),
        updatedAt: _dateTime(json['updated_at'])!,
      );

  final String opportunityId;
  final String? verificationOfficerId;
  final bool sourceChecked;
  final bool applicationLinkChecked;
  final bool deadlineChecked;
  final bool duplicateChecked;
  final String decision;
  final String? notes;
  final DateTime? verifiedAt;
  final DateTime updatedAt;

  bool get allChecksPass =>
      sourceChecked &&
      applicationLinkChecked &&
      deadlineChecked &&
      duplicateChecked;
}

/// One append-only entry from the live backend's verification history -
/// either a status transition, an officer note, or a field edit.
class LiveVerificationHistoryEntry {
  const LiveVerificationHistoryEntry({
    required this.previousStatus,
    required this.newStatus,
    required this.reason,
    required this.changedFields,
    required this.changedAt,
  });

  factory LiveVerificationHistoryEntry.fromJson(Map<String, dynamic> json) =>
      LiveVerificationHistoryEntry(
        previousStatus: json['previous_status'] as String,
        newStatus: json['new_status'] as String,
        reason: json['reason'] as String,
        changedFields: json['changed_fields'] as Map<String, dynamic>?,
        changedAt: _dateTime(json['changed_at'])!,
      );

  final String previousStatus;
  final String newStatus;
  final String reason;
  final Map<String, dynamic>? changedFields;
  final DateTime changedAt;

  bool get isNoteOnly => changedFields?['note_added'] == true;
  bool get isEdit =>
      changedFields != null &&
      !isNoteOnly &&
      !changedFields!.containsKey('verification_checks');
}

/// One field's provenance: the exact value extracted from the official
/// source's raw payload, never inferred.
class LiveFieldEvidence {
  const LiveFieldEvidence({
    required this.field,
    required this.value,
    required this.confidence,
  });

  factory LiveFieldEvidence.fromJson(Map<String, dynamic> json) =>
      LiveFieldEvidence(
        field: json['field'] as String,
        value: json['value'],
        confidence: json['confidence'] as String,
      );

  final String field;
  final Object? value;
  final String confidence;
}

/// "Where did this fact come from?" - the official source record behind
/// an opportunity, exactly as collected, alongside per-field extractions.
class LiveOpportunityEvidence {
  const LiveOpportunityEvidence({
    required this.sourceCode,
    required this.sourceName,
    required this.sourceType,
    required this.sourceTrustLevel,
    required this.officialSourceUrl,
    required this.collectedAt,
    required this.fieldEvidence,
    required this.rawPayload,
  });

  factory LiveOpportunityEvidence.fromJson(Map<String, dynamic> json) =>
      LiveOpportunityEvidence(
        sourceCode: json['source_code'] as String,
        sourceName: json['source_name'] as String,
        sourceType: json['source_type'] as String,
        sourceTrustLevel: json['source_trust_level'] as String,
        officialSourceUrl: json['official_source_url'] as String?,
        collectedAt: _dateTime(json['collected_at'])!,
        fieldEvidence: (json['field_evidence'] as List<dynamic>)
            .map((e) => LiveFieldEvidence.fromJson(e as Map<String, dynamic>))
            .toList(),
        rawPayload: json['raw_payload'] as Map<String, dynamic>,
      );

  final String sourceCode;
  final String sourceName;
  final String sourceType;
  final String sourceTrustLevel;
  final String? officialSourceUrl;
  final DateTime collectedAt;
  final List<LiveFieldEvidence> fieldEvidence;
  final Map<String, dynamic> rawPayload;
}

DateTime? _dateTime(dynamic value) =>
    value == null ? null : DateTime.tryParse(value as String);

/// One day's real decision count, for the dashboard's recent-activity chart.
class VerificationActivityDay {
  const VerificationActivityDay({required this.date, required this.decisions});

  factory VerificationActivityDay.fromJson(Map<String, dynamic> json) =>
      VerificationActivityDay(
        date: DateTime.parse(json['date'] as String),
        decisions: json['decisions'] as int,
      );

  final DateTime date;
  final int decisions;
}

/// Real, server-computed counts backing the Verification Officer dashboard.
/// Every field here is a genuine aggregate over the live backend's schema -
/// there is no per-officer assignment or richer demo workflow-status
/// concept to report on, so this deliberately differs in shape from
/// [VerificationReview]'s two-person-workflow fields. See
/// [ApiVerificationRepository.getSummary].
class LiveVerificationSummary {
  const LiveVerificationSummary({
    required this.pending,
    required this.verifiedToday,
    required this.reverificationDueSoon,
    required this.byStatus,
    required this.officialSourceRatio,
    required this.decisionsLast7Days,
    required this.approvedByYou,
  });

  factory LiveVerificationSummary.fromJson(Map<String, dynamic> json) =>
      LiveVerificationSummary(
        pending: json['pending'] as int,
        verifiedToday: json['verified_today'] as int,
        reverificationDueSoon: json['reverification_due_soon'] as int,
        byStatus: (json['by_status'] as Map<String, dynamic>).map(
          (key, value) => MapEntry(key, value as int),
        ),
        officialSourceRatio: (json['official_source_ratio'] as num).toDouble(),
        decisionsLast7Days: (json['decisions_last_7_days'] as List<dynamic>)
            .map(
              (item) => VerificationActivityDay.fromJson(
                item as Map<String, dynamic>,
              ),
            )
            .toList(),
        approvedByYou: json['approved_by_you'] as int,
      );

  final int pending;
  final int verifiedToday;
  final int reverificationDueSoon;
  final Map<String, int> byStatus;
  final double officialSourceRatio;
  final List<VerificationActivityDay> decisionsLast7Days;
  final int approvedByYou;
}

/// Source- and country-level discovery aggregates, complementing
/// [LiveVerificationSummary] (per-opportunity verification state) with
/// crawl/source health, the catalog's country spread, and application-link
/// health backlog/breakage from the backend's periodic link-health check.
/// See [ApiVerificationRepository.getDiscoverySummary].
class LiveDiscoverySummary {
  const LiveDiscoverySummary({
    required this.sourcesTotal,
    required this.sourcesActive,
    required this.sourcesWithRecentErrors,
    required this.opportunitiesTotal,
    required this.publishedTotal,
    required this.duplicateReviewRequired,
    required this.opportunitiesByCountry,
    required this.neverLinkChecked,
    required this.brokenLinks,
  });

  factory LiveDiscoverySummary.fromJson(Map<String, dynamic> json) =>
      LiveDiscoverySummary(
        sourcesTotal: json['sources_total'] as int,
        sourcesActive: json['sources_active'] as int,
        sourcesWithRecentErrors: json['sources_with_recent_errors'] as int,
        opportunitiesTotal: json['opportunities_total'] as int,
        publishedTotal: json['published_total'] as int,
        duplicateReviewRequired: json['duplicate_review_required'] as int,
        opportunitiesByCountry:
            (json['opportunities_by_country'] as Map<String, dynamic>).map(
              (key, value) => MapEntry(key, value as int),
            ),
        neverLinkChecked: json['never_link_checked'] as int,
        brokenLinks: json['broken_links'] as int,
      );

  final int sourcesTotal;
  final int sourcesActive;
  final int sourcesWithRecentErrors;
  final int opportunitiesTotal;
  final int publishedTotal;
  final int duplicateReviewRequired;
  final Map<String, int> opportunitiesByCountry;
  final int neverLinkChecked;
  final int brokenLinks;
}

/// Reads and acts on the real verification queue from the ScholarSphere
/// Python backend (scholarsphere_backend/).
///
/// This is deliberately *not* a full implementation of
/// [VerificationRepository]. That interface (and [DemoVerificationRepository]
/// behind it) models a two-person-integrity workflow: assign an officer,
/// work through a 13-item checklist, submit for a *different* officer's
/// second approval, then handle appeals and conflict resolution. The live
/// backend has none of that - it has one officer, a 4-item checklist
/// (source/application-link/deadline/duplicate), and a single decision:
/// approve, reject, request re-verification, mark expired, mark source
/// unavailable, or flag as suspicious.
///
/// Rather than fabricate a source authority, an evidence location, or a
/// second-approval workflow the backend doesn't track - which would violate
/// this project's core "never invent verification" rule just as much as
/// inventing an opportunity would - the two-person-workflow methods below
/// throw [UnsupportedError] with a message pointing back to
/// [DemoVerificationRepository]. [LiveVerificationQueueScreen] is built
/// against this class's real, additional methods directly
/// ([getReviewState], [submitDecision], [addNote], [editFields],
/// [getVerificationHistory], [getEvidence]), not against the interface.
class ApiVerificationRepository implements VerificationRepository {
  ApiVerificationRepository({
    String? baseUrl,
    http.Client? client,
    firebase.FirebaseAuth? auth,
  }) : baseUrl = baseUrl ?? _defaultBaseUrl,
       _client = client ?? http.Client(),
       _authOverride = auth {
    if (kReleaseMode) {
      TransportSecurityPolicy.requireHttps(Uri.parse(this.baseUrl));
    }
  }

  static const _defaultBaseUrl = String.fromEnvironment(
    'SCHOLARSPHERE_API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  final String baseUrl;
  final http.Client _client;
  final firebase.FirebaseAuth? _authOverride;

  firebase.FirebaseAuth get _auth =>
      _authOverride ?? firebase.FirebaseAuth.instance;

  @override
  Future<List<Opportunity>> getQueue() async {
    final body = await _get(
      '/external-opportunities/pending-verification',
      const {'page_size': '100'},
    );
    final items = (body as Map<String, dynamic>)['items'] as List<dynamic>;
    return items
        .map((item) => _toOpportunity(item as Map<String, dynamic>))
        .whereType<Opportunity>()
        .toList();
  }

  /// Every verified-but-not-yet-published opportunity, across every
  /// source - the admin-only publication queue. Paginates through the
  /// full admin listing (verification_status/publication_status aren't
  /// filterable server-side on this endpoint) rather than assuming one
  /// page covers everything.
  Future<List<Opportunity>> getAwaitingPublication() async {
    final results = <Opportunity>[];
    var page = 1;
    const pageSize = 100;
    while (true) {
      final body =
          await _get('/external-opportunities/opportunities', {
                'page': '$page',
                'page_size': '$pageSize',
              })
              as Map<String, dynamic>;
      final items = body['items'] as List<dynamic>;
      results.addAll(
        items
            .cast<Map<String, dynamic>>()
            .where(
              (item) =>
                  item['verification_status'] == 'verified' &&
                  item['publication_status'] == 'unpublished',
            )
            .map(_toOpportunity)
            .whereType<Opportunity>(),
      );
      final total = body['total'] as int;
      if (items.length < pageSize || page * pageSize >= total) break;
      page++;
    }
    return results;
  }

  /// Makes a verified opportunity visible to applicants (or reverses
  /// that). The backend rejects publishing anything not yet verified.
  Future<void> setPublished(String opportunityId, bool published) async {
    await _post(
      '/external-opportunities/opportunities/$opportunityId/publication',
      {'published': published},
    );
  }

  /// The live review state for one opportunity, or `null` if none exists
  /// yet (an opportunity always gets a review row at import time, so this
  /// is effectively always non-null for imported opportunities).
  Future<LiveVerificationReview?> getReviewState(String opportunityId) async {
    try {
      final body = await _get(
        '/external-opportunities/opportunities/$opportunityId/review',
        const {},
      );
      return LiveVerificationReview.fromJson(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  /// Records the officer's real decision: `approved`, `rejected`,
  /// `reverification_required`, `expired`, `source_unavailable`, or
  /// `suspicious`. Only `approved` requires all four checks to be true -
  /// the backend enforces this and returns 409 otherwise.
  Future<void> submitDecision({
    required String opportunityId,
    required String decision,
    required String notes,
    bool sourceChecked = false,
    bool applicationLinkChecked = false,
    bool deadlineChecked = false,
    bool duplicateChecked = false,
  }) async {
    await _post(
      '/external-opportunities/opportunities/$opportunityId/verification',
      {
        'decision': decision,
        'notes': notes,
        'source_checked': sourceChecked,
        'application_link_checked': applicationLinkChecked,
        'deadline_checked': deadlineChecked,
        'duplicate_checked': duplicateChecked,
      },
    );
  }

  /// Attaches a timestamped officer note as evidence, without changing the
  /// opportunity's verification status.
  Future<void> addNote(String opportunityId, String note) async {
    await _post('/external-opportunities/opportunities/$opportunityId/notes', {
      'note': note,
    });
  }

  /// Corrects specific fields, with a mandatory, fully audited [reason].
  /// Returns the list of field names that were actually changed.
  Future<List<String>> editFields({
    required String opportunityId,
    required String reason,
    String? title,
    String? description,
    DateTime? openingDate,
    DateTime? deadline,
    String? fundingType,
    double? awardFloor,
    double? awardCeiling,
    String? currency,
    String? officialSourceUrl,
    String? officialApplicationUrl,
  }) async {
    final body = <String, dynamic>{'reason': reason};
    if (title != null) body['title'] = title;
    if (description != null) body['description'] = description;
    if (openingDate != null) {
      body['opening_date'] = _dateOnly(openingDate);
    }
    if (deadline != null) body['deadline'] = _dateOnly(deadline);
    if (fundingType != null) body['funding_type'] = fundingType;
    if (awardFloor != null) body['award_floor'] = awardFloor;
    if (awardCeiling != null) body['award_ceiling'] = awardCeiling;
    if (currency != null) body['currency'] = currency;
    if (officialSourceUrl != null) {
      body['official_source_url'] = officialSourceUrl;
    }
    if (officialApplicationUrl != null) {
      body['official_application_url'] = officialApplicationUrl;
    }
    final response = await _patch(
      '/external-opportunities/opportunities/$opportunityId',
      body,
    );
    return List<String>.from(
      (response as Map<String, dynamic>)['changed_fields'] as List<dynamic>,
    );
  }

  /// The full append-only verification history for one opportunity.
  Future<List<LiveVerificationHistoryEntry>> getVerificationHistory(
    String opportunityId,
  ) async {
    final body = await _get(
      '/external-opportunities/opportunities/$opportunityId/verification-history',
      const {},
    );
    final items = (body as Map<String, dynamic>)['items'] as List<dynamic>;
    return items
        .map(
          (item) => LiveVerificationHistoryEntry.fromJson(
            item as Map<String, dynamic>,
          ),
        )
        .toList();
  }

  /// Real, aggregate dashboard counts - see [LiveVerificationSummary].
  Future<LiveVerificationSummary> getSummary() async {
    final body = await _get(
      '/external-opportunities/verification-summary',
      const {},
    );
    return LiveVerificationSummary.fromJson(body as Map<String, dynamic>);
  }

  /// Source/country/link-health aggregates - see [LiveDiscoverySummary].
  Future<LiveDiscoverySummary> getDiscoverySummary() async {
    final body = await _get(
      '/external-opportunities/discovery-summary',
      const {},
    );
    return LiveDiscoverySummary.fromJson(body as Map<String, dynamic>);
  }

  /// The official source's raw record behind one opportunity, available to
  /// verification staff regardless of publication status (unlike the
  /// applicant-facing evidence endpoint, which only works once published).
  Future<LiveOpportunityEvidence> getEvidence(String opportunityId) async {
    final body = await _get(
      '/external-opportunities/opportunities/$opportunityId/evidence',
      const {},
    );
    return LiveOpportunityEvidence.fromJson(body as Map<String, dynamic>);
  }

  @override
  Future<VerificationReview?> getLatestReview(String opportunityId) {
    throw UnsupportedError(
      'The live backend has no two-person review record to return here. '
      'Use getReviewState() for the real single-officer review state.',
    );
  }

  @override
  Future<void> submitReview(VerificationReview review) {
    throw UnsupportedError(
      'Use submitDecision() - the live backend has a single-officer '
      'decision, not the two-person VerificationReview workflow.',
    );
  }

  @override
  Future<VerificationReview> assign({
    required String opportunityId,
    required String officerId,
    required String assignedByUserId,
  }) => throw UnsupportedError(
    'The live backend does not track officer assignment. Any officer with '
    'the verificationOfficer role can act on any queued opportunity.',
  );

  @override
  Future<VerificationReview> submitForSecondApproval(
    VerificationReview review,
  ) => throw UnsupportedError(
    'The live backend has no second-approval step; submitDecision() is '
    'final. Use DemoVerificationRepository for the two-person demo flow.',
  );

  @override
  Future<VerificationReview> approveSecondLevel({
    required String verificationId,
    required String approverId,
  }) => throw UnsupportedError(
    'The live backend has no second-approval step to approve.',
  );

  @override
  Future<List<VerificationReview>> getHistory(String opportunityId) {
    throw UnsupportedError(
      'Use getVerificationHistory() for the live backend\'s real, '
      'differently-shaped audit trail.',
    );
  }

  @override
  Future<VerificationReview> requestCorrection({
    required String opportunityId,
    required String requestedBy,
    required String notes,
  }) => throw UnsupportedError(
    'Use editFields() to correct specific fields on the live backend, or '
    'submitDecision(decision: "reverification_required", ...) to send an '
    'opportunity back for another look.',
  );

  @override
  Future<VerificationReview> appeal({
    required String opportunityId,
    required String requestedBy,
    required String reason,
  }) => throw UnsupportedError('The live backend has no appeal workflow.');

  @override
  Future<VerificationReview> resolveConflict({
    required String opportunityId,
    required String resolverId,
    required VerificationWorkflowStatus resolution,
    required String notes,
  }) => throw UnsupportedError(
    'The live backend has no multi-reviewer conflict to resolve.',
  );

  @override
  Future<List<VerificationReview>> getAllForAdministration() {
    throw UnsupportedError(
      'Use the live backend\'s verification-history and audit-log '
      'endpoints directly for administration reporting.',
    );
  }

  /// Field mapping honesty matches [ApiOpportunityRepository._toOpportunity]:
  /// fields the backend's real sources don't publish are filled with an
  /// explicit "Not specified by source" marker, never invented. Records
  /// missing a deadline are skipped (queue items always have one in
  /// practice, since deadline is required to import, but this stays
  /// defensive rather than assume that).
  Opportunity? _toOpportunity(Map<String, dynamic> json) {
    final deadline = _date(json['deadline']);
    final opening = _date(json['opening_date']) ?? _date(json['collected_at']);
    if (deadline == null || opening == null) return null;
    final rawType = (json['opportunity_type'] as String?)?.toLowerCase() ?? '';
    final country = json['country'] as String? ?? _notSpecified;
    final provider = json['provider_name'] as String? ?? _notSpecified;

    return Opportunity(
      id: json['id'] as String,
      title: json['title'] as String,
      provider: provider,
      hostInstitution: provider,
      hostCountry: country,
      type: _mapType(rawType),
      funding: FundingType.partiallyFunded,
      deadline: deadline,
      applicationOpenDate: opening,
      verificationStatus: _mapVerificationStatus(
        json['verification_status'] as String?,
      ),
      lastVerifiedAt: null,
      officialSourceUrl: json['official_source_url'] as String? ?? '',
      applicationUrl:
          json['official_application_url'] as String? ??
          json['official_source_url'] as String? ??
          '',
      eligibleNationalities: const [],
      studyLevels: const [],
      fieldsOfStudy: const [],
      summary: json['description'] as String? ?? _notSpecified,
      benefits: const [],
      eligibilityRequirements: const [
        'Eligibility criteria are not yet structured for this source. '
            'Review the official source link before approving.',
      ],
      requiredDocuments: const [],
      applicationProcedure: const [],
      languageRequirements: const [],
      minimumAge: null,
      maximumAge: null,
      workExperienceYearsRequired: null,
      contactInformation: _notSpecified,
      availablePositions: null,
      deliveryFormat: DeliveryFormat.physical,
      applicationFee: null,
    );
  }

  /// `null` covers the pending-verification queue endpoint, whose items
  /// never carry this field since it's implied by the endpoint's own
  /// filter (verification_status == pending, per PendingOpportunityItem).
  static VerificationStatus _mapVerificationStatus(String? raw) {
    switch (raw) {
      case 'verified':
        return VerificationStatus.verified;
      case 'rejected':
        return VerificationStatus.rejected;
      case 'reverification_required':
        return VerificationStatus.verificationExpired;
      case 'expired':
      case 'source_unavailable':
        return VerificationStatus.expired;
      case 'suspicious':
        return VerificationStatus.suspicious;
      case 'archived':
        return VerificationStatus.archived;
      case null:
      case 'pending':
      default:
        return VerificationStatus.pending;
    }
  }

  static OpportunityType _mapType(String rawType) {
    if (rawType.contains('internship')) return OpportunityType.internship;
    if (rawType.contains('training')) return OpportunityType.training;
    if (rawType == 'job') return OpportunityType.job;
    return OpportunityType.grant;
  }

  static DateTime? _date(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  static String _dateOnly(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-'
      '${value.month.toString().padLeft(2, '0')}-'
      '${value.day.toString().padLeft(2, '0')}';

  Future<dynamic> _get(String path, Map<String, String> query) async {
    final uri = Uri.parse(
      '$baseUrl$path',
    ).replace(queryParameters: query.isEmpty ? null : query);
    final headers = await _headers();
    return _send(() => _client.get(uri, headers: headers));
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseUrl$path');
    final headers = await _headers();
    headers['Content-Type'] = 'application/json';
    return _send(
      () => _client.post(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _patch(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseUrl$path');
    final headers = await _headers();
    headers['Content-Type'] = 'application/json';
    return _send(
      () => _client.patch(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _send(Future<http.Response> Function() request) async {
    late final http.Response response;
    try {
      response = await request();
    } on Exception catch (error) {
      throw LiveBackendException(
        'Could not reach the ScholarSphere backend: $error',
      );
    }
    if (response.statusCode == 401) {
      throw const LiveBackendException(
        'Sign-in expired. Sign in again to continue.',
        statusCode: 401,
      );
    }
    if (response.statusCode == 404) {
      throw const LiveBackendException('Not found.', statusCode: 404);
    }
    if (response.statusCode == 409) {
      throw LiveBackendException(
        _errorDetail(response.body) ??
            'The action conflicts with the current state.',
        statusCode: 409,
      );
    }
    if (response.statusCode >= 400) {
      throw LiveBackendException(
        _errorDetail(response.body) ??
            'The ScholarSphere backend returned an error.',
        statusCode: response.statusCode,
      );
    }
    if (response.body.isEmpty) return null;
    return jsonDecode(response.body);
  }

  static String? _errorDetail(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        final detail = decoded['detail'] ?? decoded['error']?['message'];
        if (detail is String) return detail;
      }
    } on FormatException {
      // Fall through to the generic message.
    }
    return null;
  }

  Future<Map<String, String>> _headers() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const LiveBackendException(
        'Sign in to manage verification.',
        statusCode: 401,
      );
    }
    final token = await user.getIdToken();
    return {'Authorization': 'Bearer $token', 'Accept': 'application/json'};
  }

  void dispose() => _client.close();
}
