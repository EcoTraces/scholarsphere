import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../opportunities/domain/opportunity.dart';
import '../../security/domain/security_backend_contracts.dart';
import '../domain/application_record.dart';
import '../domain/application_repository.dart';

/// Reads and writes real, per-user application records from the
/// ScholarSphere Python backend (scholarsphere_backend/).
///
/// This is the live replacement for [DemoApplicationRepository]. It only
/// ever needs to work with opportunities that exist in the live backend
/// (real Postgres-issued UUIDs) - the applicant-facing screens that call
/// [saveOpportunity] already source their [Opportunity] objects from
/// [ApiOpportunityRepository], never from the in-memory demo catalog, so
/// there is no dangling-reference risk here.
///
/// The backend, not this client, decides which records a caller may see or
/// edit: every request is scoped to the caller's own Firebase UID from the
/// bearer token, never from a client-supplied [String] userId parameter.
class ApiApplicationRepository implements ApplicationRepository {
  ApiApplicationRepository({
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

  /// Override at build/run time with
  /// `--dart-define=SCHOLARSPHERE_API_BASE_URL=https://api.example.org/api/v1`.
  static const _defaultBaseUrl = String.fromEnvironment(
    'SCHOLARSPHERE_API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  final String baseUrl;
  final http.Client _client;
  final firebase.FirebaseAuth? _authOverride;

  // Resolved lazily, not in the constructor - see ApiOpportunityRepository
  // for why (keeps construction safe without a live Firebase app).
  firebase.FirebaseAuth get _auth =>
      _authOverride ?? firebase.FirebaseAuth.instance;

  @override
  Future<List<ApplicationRecord>> getForUser(String userId) async {
    final body = await _get('/applications');
    final items = body as List<dynamic>;
    return items
        .map((item) => _toRecord(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<ApplicationRecord?> getForOpportunity(
    String userId,
    String opportunityId,
  ) async {
    try {
      final body = await _get('/applications/by-opportunity/$opportunityId');
      return _toRecord(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<ApplicationRecord> saveOpportunity(
    String userId,
    Opportunity opportunity,
  ) async {
    final body = await _post('/applications', {
      'opportunity_id': opportunity.id,
    });
    return _toRecord(body as Map<String, dynamic>);
  }

  @override
  Future<void> update(ApplicationRecord record) async {
    try {
      await _patch('/applications/${record.id}', {
        'stage': _stageToWire(record.stage),
        'application_date': _dateString(record.applicationDate),
        'application_reference_number': record.applicationReferenceNumber,
        'missing_documents': record.missingDocuments,
        'interview_date': _dateString(record.interviewDate),
        'personal_notes': record.personalNotes,
        'result_date': _dateString(record.resultDate),
        'scholarship_value': record.scholarshipValue,
        'follow_up_actions': record.followUpActions,
      });
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw StateError('Application record not found.');
      }
      rethrow;
    }
  }

  @override
  Future<List<ApplicationRecord>> getAllForAdministration() async {
    final records = <ApplicationRecord>[];
    var page = 1;
    const pageSize = 100;
    while (true) {
      final body =
          await _get('/applications/admin', {
                'page': '$page',
                'page_size': '$pageSize',
              })
              as Map<String, dynamic>;
      final items = (body['items'] as List<dynamic>)
          .map((item) => _toRecord(item as Map<String, dynamic>))
          .toList();
      records.addAll(items);
      if (items.length < pageSize) break;
      page += 1;
    }
    return records;
  }

  ApplicationRecord _toRecord(Map<String, dynamic> json) => ApplicationRecord(
    id: json['id'] as String,
    userId: json['user_id'] as String,
    opportunityId: json['opportunity_id'] as String,
    opportunityTitle: json['opportunity_title'] as String,
    provider: json['provider_name'] as String,
    deadline: _date(json['deadline']) ?? DateTime.now(),
    stage: _stageFromWire(json['stage'] as String),
    createdAt: DateTime.parse(json['created_at'] as String),
    updatedAt: DateTime.parse(json['updated_at'] as String),
    applicationDate: _date(json['application_date']),
    applicationReferenceNumber: json['application_reference_number'] as String?,
    missingDocuments: (json['missing_documents'] as List<dynamic>)
        .cast<String>(),
    interviewDate: _date(json['interview_date']),
    personalNotes: json['personal_notes'] as String,
    resultDate: _date(json['result_date']),
    scholarshipValue: (json['scholarship_value'] as num?)?.toDouble(),
    followUpActions: (json['follow_up_actions'] as List<dynamic>)
        .cast<String>(),
  );

  // Keep in sync with `_STAGE_WIRE_TO_MODEL` in
  // scholarsphere_backend/app/schemas/application.py.
  static ApplicationStage _stageFromWire(String value) => switch (value) {
    'interested' => ApplicationStage.interested,
    'saved' => ApplicationStage.saved,
    'preparingDocuments' => ApplicationStage.preparingDocuments,
    'applicationStarted' => ApplicationStage.applicationStarted,
    'applicationSubmitted' => ApplicationStage.applicationSubmitted,
    'interviewStage' => ApplicationStage.interviewStage,
    'waitingForDecision' => ApplicationStage.waitingForDecision,
    'accepted' => ApplicationStage.accepted,
    'rejected' => ApplicationStage.rejected,
    'withdrawn' => ApplicationStage.withdrawn,
    _ => throw LiveBackendException('Unknown application stage: $value'),
  };

  static String _stageToWire(ApplicationStage stage) => switch (stage) {
    ApplicationStage.interested => 'interested',
    ApplicationStage.saved => 'saved',
    ApplicationStage.preparingDocuments => 'preparingDocuments',
    ApplicationStage.applicationStarted => 'applicationStarted',
    ApplicationStage.applicationSubmitted => 'applicationSubmitted',
    ApplicationStage.interviewStage => 'interviewStage',
    ApplicationStage.waitingForDecision => 'waitingForDecision',
    ApplicationStage.accepted => 'accepted',
    ApplicationStage.rejected => 'rejected',
    ApplicationStage.withdrawn => 'withdrawn',
  };

  static DateTime? _date(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  static String? _dateString(DateTime? date) => date == null
      ? null
      : '${date.year.toString().padLeft(4, '0')}-'
            '${date.month.toString().padLeft(2, '0')}-'
            '${date.day.toString().padLeft(2, '0')}';

  Future<dynamic> _get(
    String path, [
    Map<String, String> query = const {},
  ]) async {
    final headers = await _headers();
    final uri = Uri.parse(
      '$baseUrl$path',
    ).replace(queryParameters: query.isEmpty ? null : query);
    return _handle(() => _client.get(uri, headers: headers));
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.post(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _patch(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.patch(uri, headers: headers, body: jsonEncode(body)),
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
        'Sign-in expired. Sign in again to view applications.',
        statusCode: 401,
      );
    }
    if (response.statusCode >= 400) {
      throw LiveBackendException(
        'The ScholarSphere backend returned an error.',
        statusCode: response.statusCode,
      );
    }
    return jsonDecode(response.body);
  }

  Future<Map<String, String>> _headers() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const LiveBackendException(
        'Sign in to view applications.',
        statusCode: 401,
      );
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
