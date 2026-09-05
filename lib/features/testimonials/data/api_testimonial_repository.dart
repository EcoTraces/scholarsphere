import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../security/domain/security_backend_contracts.dart';
import '../domain/testimonial.dart';
import '../domain/testimonial_repository.dart';

/// A network failure talking to the ScholarSphere testimonials backend -
/// the same shape as ApiOpportunityRepository's LiveBackendException, so
/// UI error-handling code can treat every ScholarSphere API surface the
/// same way.
class TestimonialBackendException implements Exception {
  const TestimonialBackendException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ApiTestimonialRepository implements TestimonialRepository {
  ApiTestimonialRepository({
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
  Future<SuccessStoryPage> listSuccessStories(
    SuccessStoryFilters filters, {
    int page = 1,
    int pageSize = 25,
  }) async {
    final body =
        await _get('/success-stories', {
              ...filters.toQuery(),
              'page': '$page',
              'page_size': '$pageSize',
            })
            as Map<String, dynamic>;
    final items = (body['items'] as List<dynamic>)
        .map((item) => _toSummary(item as Map<String, dynamic>))
        .toList();
    return SuccessStoryPage(
      items: items,
      total: body['total'] as int,
      page: body['page'] as int,
      pageSize: body['page_size'] as int,
    );
  }

  @override
  Future<TestimonialStats> getStats() async {
    final body = await _get('/success-stories/stats', const {});
    return _toStats(body as Map<String, dynamic>);
  }

  @override
  Future<SuccessStoryDetail> getStory(String slug) async {
    final body = await _get(
      '/success-stories/${Uri.encodeComponent(slug)}',
      const {},
    );
    return _toDetail(body as Map<String, dynamic>);
  }

  @override
  Future<List<SuccessStorySummary>> getRelatedStories(
    String slug, {
    int limit = 4,
  }) async {
    final body = await _get(
      '/success-stories/${Uri.encodeComponent(slug)}/related',
      {'limit': '$limit'},
    );
    return (body as List<dynamic>)
        .map((item) => _toSummary(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<SuccessStoryDetail> react(
    String slug,
    TestimonialReactionType type,
  ) async {
    final body = await _post(
      '/success-stories/${Uri.encodeComponent(slug)}/react',
      {'reaction_type': type.wire},
    );
    return _toDetail(body as Map<String, dynamic>);
  }

  @override
  Future<SuccessStoryDetail> removeReaction(String slug) async {
    final body = await _delete(
      '/success-stories/${Uri.encodeComponent(slug)}/react',
    );
    return _toDetail(body as Map<String, dynamic>);
  }

  @override
  Future<List<MyTestimonial>> listMine() async {
    final body = await _get('/testimonials/me', const {});
    return (body as List<dynamic>)
        .map((item) => _toMine(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<MyTestimonial> getMine(String testimonialId) async {
    final body = await _get('/testimonials/me/$testimonialId', const {});
    return _toMine(body as Map<String, dynamic>);
  }

  @override
  Future<MyTestimonial> saveDraft(
    TestimonialDraftInput input, {
    String? id,
  }) async {
    final path = id == null
        ? '/testimonials/me/draft'
        : '/testimonials/me/$id/draft';
    final body = id == null
        ? await _post(path, input.toJson())
        : await _put(path, input.toJson());
    return _toMine(body as Map<String, dynamic>);
  }

  @override
  Future<MyTestimonial> submit(String testimonialId) async {
    final body = await _post('/testimonials/me/$testimonialId/submit', {
      'consent_confirmed': true,
    });
    return _toMine(body as Map<String, dynamic>);
  }

  @override
  Future<MyTestimonial> withdraw(String testimonialId) async {
    final body = await _post(
      '/testimonials/me/$testimonialId/withdraw',
      const {},
    );
    return _toMine(body as Map<String, dynamic>);
  }

  @override
  Future<String> getMyEvidenceUrl(String testimonialId, String path) async {
    final body = await _get('/testimonials/me/$testimonialId/evidence-url', {
      'path': path,
    });
    return (body as Map<String, dynamic>)['url'] as String;
  }

  @override
  Future<AdminTestimonialPage> listForModeration(
    AdminTestimonialFilters filters, {
    int page = 1,
    int pageSize = 25,
  }) async {
    final query = <String, String>{
      if (filters.status != null) 'status': _statusWire(filters.status!),
      if (filters.opportunityType != null)
        'opportunity_type': filters.opportunityType!,
      if (filters.country != null) 'country': filters.country!,
      if (filters.verificationStatus != null)
        'verification_status':
            filters.verificationStatus == TestimonialVerificationStatus.verified
            ? 'verified'
            : 'unverified',
      'page': '$page',
      'page_size': '$pageSize',
    };
    final body =
        await _get('/admin/testimonials', query) as Map<String, dynamic>;
    final items = (body['items'] as List<dynamic>)
        .map((item) => _toAdmin(item as Map<String, dynamic>))
        .toList();
    return AdminTestimonialPage(
      items: items,
      total: body['total'] as int,
      page: body['page'] as int,
      pageSize: body['page_size'] as int,
    );
  }

  @override
  Future<AdminTestimonial> getForModeration(String testimonialId) async {
    final body = await _get('/admin/testimonials/$testimonialId', const {});
    return _toAdmin(body as Map<String, dynamic>);
  }

  @override
  Future<List<TestimonialModerationHistoryItem>> getModerationHistory(
    String testimonialId,
  ) async {
    final body = await _get(
      '/admin/testimonials/$testimonialId/history',
      const {},
    );
    return (body as List<dynamic>)
        .map(
          (item) => TestimonialModerationHistoryItem(
            id: item['id'] as String,
            previousStatus: item['previous_status'] as String,
            newStatus: item['new_status'] as String,
            actorId: item['actor_id'] as String,
            notes: item['notes'] as String,
            createdAt: DateTime.parse(item['created_at'] as String),
          ),
        )
        .toList();
  }

  @override
  Future<AdminTestimonial> markUnderReview(String testimonialId) async {
    final body = await _post(
      '/admin/testimonials/$testimonialId/review',
      const {},
    );
    return _toAdmin(body as Map<String, dynamic>);
  }

  @override
  Future<AdminTestimonial> approve(String testimonialId, String notes) async {
    final body = await _post('/admin/testimonials/$testimonialId/approve', {
      'reason': notes,
    });
    return _toAdmin(body as Map<String, dynamic>);
  }

  @override
  Future<AdminTestimonial> reject(String testimonialId, String reason) async {
    final body = await _post('/admin/testimonials/$testimonialId/reject', {
      'reason': reason,
    });
    return _toAdmin(body as Map<String, dynamic>);
  }

  @override
  Future<AdminTestimonial> requestChanges(
    String testimonialId,
    String reason,
  ) async {
    final body = await _post(
      '/admin/testimonials/$testimonialId/request-changes',
      {'reason': reason},
    );
    return _toAdmin(body as Map<String, dynamic>);
  }

  @override
  Future<AdminTestimonial> verify(
    String testimonialId,
    String verificationMethod,
    String? notes,
  ) async {
    final body = await _post('/admin/testimonials/$testimonialId/verify', {
      'verification_method': verificationMethod,
      if (notes != null && notes.isNotEmpty) 'notes': notes,
    });
    return _toAdmin(body as Map<String, dynamic>);
  }

  @override
  Future<AdminTestimonial> feature(String testimonialId) async {
    final body = await _post(
      '/admin/testimonials/$testimonialId/feature',
      const {},
    );
    return _toAdmin(body as Map<String, dynamic>);
  }

  @override
  Future<AdminTestimonial> unfeature(String testimonialId) async {
    final body = await _post(
      '/admin/testimonials/$testimonialId/unfeature',
      const {},
    );
    return _toAdmin(body as Map<String, dynamic>);
  }

  @override
  Future<AdminTestimonial> archive(String testimonialId, String reason) async {
    final body = await _post('/admin/testimonials/$testimonialId/archive', {
      'reason': reason,
    });
    return _toAdmin(body as Map<String, dynamic>);
  }

  @override
  Future<AdminTestimonial> setInternalNotes(
    String testimonialId,
    String notes,
  ) async {
    final body = await _put('/admin/testimonials/$testimonialId/notes', {
      'notes': notes,
    });
    return _toAdmin(body as Map<String, dynamic>);
  }

  @override
  Future<String> getAdminEvidenceUrl(String testimonialId, String path) async {
    final body = await _get('/admin/testimonials/$testimonialId/evidence-url', {
      'path': path,
    });
    return (body as Map<String, dynamic>)['url'] as String;
  }

  // --- JSON mapping --------------------------------------------------------

  static SuccessStorySummary _toSummary(Map<String, dynamic> json) =>
      SuccessStorySummary(
        id: json['id'] as String,
        slug: json['slug'] as String,
        displayName: json['display_name'] as String,
        photoStoragePath: json['photo_storage_path'] as String?,
        country: json['country'] as String?,
        university: json['university'] as String?,
        program: json['program'] as String?,
        degreeLevel: json['degree_level'] as String?,
        fieldOfStudy: json['field_of_study'] as String?,
        opportunityName: json['opportunity_name'] as String,
        opportunityProvider: json['opportunity_provider'] as String,
        opportunityType: json['opportunity_type'] as String,
        outcome: TestimonialOutcome.fromWire(json['outcome'] as String),
        successYear: json['success_year'] as int?,
        verificationStatus: TestimonialVerificationStatus.fromWire(
          json['verification_status'] as String,
        ),
        featured: json['featured'] as bool,
        badges: (json['badges'] as List<dynamic>).cast<String>(),
        excerpt: json['excerpt'] as String,
        featuresUsed: (json['features_used'] as List<dynamic>).cast<String>(),
        helpfulCount: json['helpful_count'] as int,
        inspiringCount: json['inspiring_count'] as int,
        usefulCount: json['useful_count'] as int,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  static SuccessStoryDetail _toDetail(Map<String, dynamic> json) =>
      SuccessStoryDetail(
        id: json['id'] as String,
        slug: json['slug'] as String,
        displayName: json['display_name'] as String,
        photoStoragePath: json['photo_storage_path'] as String?,
        country: json['country'] as String?,
        university: json['university'] as String?,
        program: json['program'] as String?,
        degreeLevel: json['degree_level'] as String?,
        fieldOfStudy: json['field_of_study'] as String?,
        opportunityId: json['opportunity_id'] as String?,
        opportunityName: json['opportunity_name'] as String,
        opportunityProvider: json['opportunity_provider'] as String,
        opportunityType: json['opportunity_type'] as String,
        outcome: TestimonialOutcome.fromWire(json['outcome'] as String),
        successYear: json['success_year'] as int?,
        challenge: json['challenge'] as String?,
        discoveryStory: json['discovery_story'] as String?,
        preparationStory: json['preparation_story'] as String?,
        scholarsphereHelp: json['scholarsphere_help'] as String?,
        outcomeNarrative: json['outcome_narrative'] as String?,
        impact: json['impact'] as String?,
        advice: json['advice'] as String?,
        featuresUsed: (json['features_used'] as List<dynamic>).cast<String>(),
        verificationStatus: TestimonialVerificationStatus.fromWire(
          json['verification_status'] as String,
        ),
        featured: json['featured'] as bool,
        badges: (json['badges'] as List<dynamic>).cast<String>(),
        helpfulCount: json['helpful_count'] as int,
        inspiringCount: json['inspiring_count'] as int,
        usefulCount: json['useful_count'] as int,
        viewCount: json['view_count'] as int,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  static MyTestimonial _toMine(Map<String, dynamic> json) => MyTestimonial(
    id: json['id'] as String,
    slug: json['slug'] as String,
    status: TestimonialStatus.fromWire(json['status'] as String),
    verificationStatus: TestimonialVerificationStatus.fromWire(
      json['verification_status'] as String,
    ),
    featured: json['featured'] as bool,
    opportunityId: json['opportunity_id'] as String?,
    opportunityName: json['opportunity_name'] as String,
    opportunityProvider: json['opportunity_provider'] as String,
    opportunityType: json['opportunity_type'] as String,
    country: json['country'] as String?,
    degreeLevel: json['degree_level'] as String?,
    fieldOfStudy: json['field_of_study'] as String?,
    successYear: json['success_year'] as int?,
    outcome: TestimonialOutcome.fromWire(json['outcome'] as String),
    challenge: json['challenge'] as String?,
    discoveryStory: json['discovery_story'] as String?,
    preparationStory: json['preparation_story'] as String?,
    scholarsphereHelp: json['scholarsphere_help'] as String?,
    outcomeNarrative: json['outcome_narrative'] as String?,
    impact: json['impact'] as String?,
    advice: json['advice'] as String?,
    featuresUsed: (json['features_used'] as List<dynamic>).cast<String>(),
    fullName: json['full_name'] as String,
    university: json['university'] as String?,
    program: json['program'] as String?,
    photoStoragePath: json['photo_storage_path'] as String?,
    displayMode: TestimonialDisplayMode.fromWire(
      json['display_mode'] as String,
    ),
    showUniversity: json['show_university'] as bool,
    showCountry: json['show_country'] as bool,
    showProgram: json['show_program'] as bool,
    showPhoto: json['show_photo'] as bool,
    evidenceStoragePaths: (json['evidence_storage_paths'] as List<dynamic>)
        .cast<String>(),
    rejectionReason: json['rejection_reason'] as String?,
    submittedAt: _date(json['submitted_at']),
    approvedAt: _date(json['approved_at']),
    verifiedAt: _date(json['verified_at']),
    withdrawnAt: _date(json['withdrawn_at']),
    createdAt: DateTime.parse(json['created_at'] as String),
    updatedAt: DateTime.parse(json['updated_at'] as String),
  );

  static AdminTestimonial _toAdmin(Map<String, dynamic> json) {
    final mine = _toMine(json);
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
      userId: json['user_id'] as String,
      internalNotes: json['internal_notes'] as String?,
      verifiedBy: json['verified_by'] as String?,
      verificationMethod: json['verification_method'] as String?,
      lastModeratorId: json['last_moderator_id'] as String?,
      rejectedAt: _date(json['rejected_at']),
    );
  }

  static TestimonialStats _toStats(Map<String, dynamic> json) =>
      TestimonialStats(
        totalStories: json['total_stories'] as int?,
        verifiedStories: json['verified_stories'] as int?,
        countriesRepresented: json['countries_represented'] as int?,
        opportunityTypesRepresented:
            json['opportunity_types_represented'] as int?,
        fieldsOfStudyRepresented: json['fields_of_study_represented'] as int?,
      );

  static String _statusWire(TestimonialStatus status) => switch (status) {
    TestimonialStatus.draft => 'draft',
    TestimonialStatus.submitted => 'submitted',
    TestimonialStatus.underReview => 'under_review',
    TestimonialStatus.changesRequested => 'changes_requested',
    TestimonialStatus.approved => 'approved',
    TestimonialStatus.rejected => 'rejected',
    TestimonialStatus.withdrawn => 'withdrawn',
  };

  static DateTime? _date(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  // --- HTTP plumbing ---------------------------------------------------

  Future<dynamic> _get(String path, Map<String, String> query) async {
    final uri = Uri.parse(
      '$baseUrl$path',
    ).replace(queryParameters: query.isEmpty ? null : query);
    final headers = await _headers();
    return _decode(await _send(() => _client.get(uri, headers: headers)));
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseUrl$path');
    final headers = await _headers(json: true);
    return _decode(
      await _send(
        () => _client.post(uri, headers: headers, body: jsonEncode(body)),
      ),
    );
  }

  Future<dynamic> _put(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseUrl$path');
    final headers = await _headers(json: true);
    return _decode(
      await _send(
        () => _client.put(uri, headers: headers, body: jsonEncode(body)),
      ),
    );
  }

  Future<dynamic> _delete(String path) async {
    final uri = Uri.parse('$baseUrl$path');
    final headers = await _headers();
    return _decode(await _send(() => _client.delete(uri, headers: headers)));
  }

  Future<http.Response> _send(Future<http.Response> Function() request) async {
    try {
      return await request();
    } on Exception catch (error) {
      throw TestimonialBackendException(
        'Could not reach the ScholarSphere backend: $error',
      );
    }
  }

  dynamic _decode(http.Response response) {
    if (response.statusCode == 401) {
      throw const TestimonialBackendException(
        'Sign-in expired. Sign in again to continue.',
        statusCode: 401,
      );
    }
    if (response.statusCode == 403) {
      throw const TestimonialBackendException(
        'You are not authorized to do that.',
        statusCode: 403,
      );
    }
    if (response.statusCode == 404) {
      throw const TestimonialBackendException(
        'That success story could not be found.',
        statusCode: 404,
      );
    }
    if (response.statusCode >= 400) {
      String message = 'The ScholarSphere backend returned an error.';
      try {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        final error = decoded['error'] as Map<String, dynamic>?;
        if (error?['message'] is String) {
          message = error!['message'] as String;
        }
      } on FormatException {
        // Fall through to the generic message above.
      }
      throw TestimonialBackendException(
        message,
        statusCode: response.statusCode,
      );
    }
    if (response.body.isEmpty) return null;
    return jsonDecode(response.body);
  }

  Future<Map<String, String>> _headers({bool json = false}) async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const TestimonialBackendException(
        'Sign in to continue.',
        statusCode: 401,
      );
    }
    final token = await user.getIdToken();
    return {
      'Authorization': 'Bearer $token',
      'Accept': 'application/json',
      if (json) 'Content-Type': 'application/json',
    };
  }

  void dispose() => _client.close();
}
