import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../documents/domain/document_readiness.dart';
import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../opportunities/domain/opportunity.dart';
import '../../profiles/domain/applicant_profile.dart';
import '../../security/domain/security_backend_contracts.dart';
import '../domain/application_guidance.dart';
import '../domain/application_guidance_repository.dart';

/// Reads and writes real application-guidance checklist data from the
/// ScholarSphere Python backend. Live replacement for
/// [DemoApplicationGuidanceRepository].
///
/// The [profile] and [documents] parameters accepted by [createPlan] are
/// kept for interface compatibility but not sent to the server: the
/// backend always looks up the caller's own profile and documents from
/// their real backend records rather than trusting a client-supplied
/// snapshot. `opportunity.requiredDocuments`/`applicationProcedure` ARE
/// sent as a snapshot, because external opportunities do not yet store
/// structured application requirements server-side (this repository's
/// own [Opportunity] objects also always carry empty lists for those two
/// fields today - a pre-existing gap in the Opportunities feature).
class ApiApplicationGuidanceRepository implements ApplicationGuidanceRepository {
  ApiApplicationGuidanceRepository({
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
  Future<ApplicationGuidancePlan> createPlan({
    required String userId,
    required Opportunity opportunity,
    required ApplicantProfile profile,
    required List<UserDocument> documents,
  }) async {
    final body = await _post('/guidance/plans', {
      'opportunity_id': opportunity.id,
      'opportunity_title': opportunity.title,
      'opportunity_deadline': opportunity.deadline.toUtc().toIso8601String(),
      'required_documents': opportunity.requiredDocuments,
      'application_procedure': opportunity.applicationProcedure,
    });
    return _toPlan(body as Map<String, dynamic>);
  }

  @override
  Future<ApplicationGuidancePlan?> getPlan(
    String userId,
    String opportunityId,
  ) async {
    final body = await _get('/guidance/plans/$opportunityId');
    if (body == null) return null;
    return _toPlan(body as Map<String, dynamic>);
  }

  @override
  Future<ApplicationGuidancePlan> updateItem(
    String planId,
    String itemId,
    GuidanceItemStatus status,
  ) async {
    try {
      final body = await _post('/guidance/plans/$planId/items/$itemId', {
        'status': _statusToWire(status),
      });
      return _toPlan(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw StateError('Guidance plan was not found.');
      }
      rethrow;
    }
  }

  @override
  Future<ApplicationGuidancePlan> trackRecommendationLetter(
    String planId,
    RecommendationLetterTracker letter,
  ) async {
    try {
      final body = await _post('/guidance/plans/$planId/recommendation-letters', {
        'id': letter.id,
        'referee_name': letter.refereeName,
        'referee_email': letter.refereeEmail,
        'requested_at': letter.requestedAt.toUtc().toIso8601String(),
        'due_at': letter.dueAt.toUtc().toIso8601String(),
        'received': letter.received,
        'received_at': letter.receivedAt?.toUtc().toIso8601String(),
      });
      return _toPlan(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw StateError('Guidance plan was not found.');
      }
      rethrow;
    }
  }

  @override
  Future<ApplicationGuidancePlan> confirmSubmission(
    String planId,
    SubmissionConfirmation confirmation,
  ) async {
    try {
      final body = await _post('/guidance/plans/$planId/submission', {
        'confirmed_at': confirmation.confirmedAt.toUtc().toIso8601String(),
        'application_reference': confirmation.applicationReference,
        'confirmed_by_user_id': confirmation.confirmedByUserId,
        'official_portal': confirmation.officialPortal,
      });
      return _toPlan(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw StateError('Guidance plan was not found.');
      }
      if (error.statusCode == 422) {
        throw StateError(
          'Submission confirmation requires an official portal and reference.',
        );
      }
      rethrow;
    }
  }

  ApplicationGuidancePlan _toPlan(Map<String, dynamic> json) =>
      ApplicationGuidancePlan(
        id: json['id'] as String,
        userId: json['user_id'] as String,
        opportunityId: json['opportunity_id'] as String,
        items: (json['items'] as List<dynamic>)
            .map((item) => _toItem(item as Map<String, dynamic>))
            .toList(),
        recommendationLetters: (json['recommendation_letters'] as List<dynamic>)
            .map((item) => _toLetter(item as Map<String, dynamic>))
            .toList(),
        timelineStart: DateTime.parse(json['timeline_start'] as String),
        deadline: DateTime.parse(json['deadline'] as String),
        followUpReminders: (json['follow_up_reminders'] as List<dynamic>)
            .map((value) => DateTime.parse(value as String))
            .toList(),
        updatedAt: DateTime.parse(json['updated_at'] as String),
        submissionConfirmation: _toConfirmation(
          json['submission_confirmation'] as Map<String, dynamic>?,
        ),
      );

  GuidanceItem _toItem(Map<String, dynamic> json) => GuidanceItem(
    id: json['id'] as String,
    type: _typeFromWire(json['type'] as String),
    title: json['title'] as String,
    guidance: json['guidance'] as String,
    status: _statusFromWire(json['status'] as String),
    required: json['required'] as bool,
    order: json['order'] as int,
    dueAt: _dateTime(json['due_at']),
  );

  RecommendationLetterTracker _toLetter(Map<String, dynamic> json) =>
      RecommendationLetterTracker(
        id: json['id'] as String,
        refereeName: json['referee_name'] as String,
        refereeEmail: json['referee_email'] as String,
        requestedAt: DateTime.parse(json['requested_at'] as String),
        dueAt: DateTime.parse(json['due_at'] as String),
        received: json['received'] as bool,
        receivedAt: _dateTime(json['received_at']),
      );

  SubmissionConfirmation? _toConfirmation(Map<String, dynamic>? json) {
    if (json == null) return null;
    return SubmissionConfirmation(
      confirmedAt: DateTime.parse(json['confirmed_at'] as String),
      applicationReference: json['application_reference'] as String,
      confirmedByUserId: json['confirmed_by_user_id'] as String,
      officialPortal: json['official_portal'] as String,
    );
  }

  static DateTime? _dateTime(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  // Keep in sync with app/schemas/guidance.py's wire maps.
  static GuidanceItemType _typeFromWire(String value) => switch (value) {
    'applicationStep' => GuidanceItemType.applicationStep,
    'requiredDocument' => GuidanceItemType.requiredDocument,
    'profileInformation' => GuidanceItemType.profileInformation,
    'curriculumVitae' => GuidanceItemType.curriculumVitae,
    'personalStatement' => GuidanceItemType.personalStatement,
    'researchProposal' => GuidanceItemType.researchProposal,
    'recommendationLetter' => GuidanceItemType.recommendationLetter,
    'interviewPreparation' => GuidanceItemType.interviewPreparation,
    'submission' => GuidanceItemType.submission,
    'followUp' => GuidanceItemType.followUp,
    _ => throw LiveBackendException('Unknown guidance item type: $value'),
  };

  static String _statusToWire(GuidanceItemStatus status) => switch (status) {
    GuidanceItemStatus.notStarted => 'notStarted',
    GuidanceItemStatus.inProgress => 'inProgress',
    GuidanceItemStatus.ready => 'ready',
    GuidanceItemStatus.missing => 'missing',
    GuidanceItemStatus.confirmed => 'confirmed',
    GuidanceItemStatus.notApplicable => 'notApplicable',
  };

  static GuidanceItemStatus _statusFromWire(String value) => switch (value) {
    'notStarted' => GuidanceItemStatus.notStarted,
    'inProgress' => GuidanceItemStatus.inProgress,
    'ready' => GuidanceItemStatus.ready,
    'missing' => GuidanceItemStatus.missing,
    'confirmed' => GuidanceItemStatus.confirmed,
    'notApplicable' => GuidanceItemStatus.notApplicable,
    _ => throw LiveBackendException('Unknown guidance item status: $value'),
  };

  Future<dynamic> _get(String path) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(() => _client.get(uri, headers: headers));
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.post(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _handle(Future<http.Response> Function() request) async {
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
        'Sign-in expired. Sign in again.',
        statusCode: 401,
      );
    }
    if (response.statusCode >= 400) {
      throw LiveBackendException(
        'The ScholarSphere backend returned an error.',
        statusCode: response.statusCode,
      );
    }
    if (response.body.isEmpty) return null;
    return jsonDecode(response.body);
  }

  Future<Map<String, String>> _headers() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const LiveBackendException('Sign in first.', statusCode: 401);
    }
    final token = await user.getIdToken();
    return {
      'Authorization': 'Bearer $token',
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
  }

  void dispose() => _client.close();
}
