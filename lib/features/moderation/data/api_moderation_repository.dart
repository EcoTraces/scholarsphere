import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/moderation_case.dart';
import '../domain/moderation_repository.dart';

/// Reads and writes real moderation case/warning data from the
/// ScholarSphere Python backend (scholarsphere_backend/).
///
/// This is the live replacement for [DemoModerationRepository]. Reporting
/// an opportunity always targets the real, live `ExternalOpportunity`
/// pipeline (never a demo id) - the only screen that submits reports
/// ([ReportContentScreen], pushed from `opportunity_detail_screen.dart`)
/// already sources its `entityId` from [ApiOpportunityRepository]. Every
/// request is scoped to the caller's own Firebase UID from the bearer
/// token: [reporterId]/[moderatorId]/[appellantId]/[actorId] parameters on
/// the interface are accepted for signature compatibility but never sent -
/// the server always uses its own verified identity for who performed an
/// action, never a client-supplied id.
class ApiModerationRepository implements ModerationRepository {
  ApiModerationRepository({
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
  Future<ModerationCase> submit(ModerationCase report) async {
    try {
      final body = await _post('/moderation-cases', {
        'entity_type': _entityTypeToWire(report.entityType),
        'entity_id': report.entityId,
        'report_type': _reportTypeToWire(report.reportType),
        'description': report.description,
        'evidence': report.evidence
            .map(
              (item) => {
                'location': item.location,
                'description': item.description,
              },
            )
            .toList(),
      });
      return _toCase(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const ModerationFailure(
          'An equivalent open report already exists.',
        );
      }
      if (error.statusCode == 404) {
        throw const ModerationFailure('Reported entity was not found.');
      }
      rethrow;
    }
  }

  @override
  Future<List<ModerationCase>> getQueue() async {
    final body = await _get('/moderation-cases/queue');
    return (body as List<dynamic>)
        .map((item) => _toCase(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<List<ModerationCase>> getForReporter(String reporterId) async {
    final body = await _get('/moderation-cases/mine');
    return (body as List<dynamic>)
        .map((item) => _toCase(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<ModerationCase> assign(String caseId, String moderatorId) async {
    final body = await _post('/moderation-cases/$caseId/assign', const {});
    return _toCase(body as Map<String, dynamic>);
  }

  @override
  Future<ModerationCase> transition({
    required String caseId,
    required String actorId,
    required ModerationStatus status,
    required String notes,
    bool hideContent = false,
  }) async {
    final body = await _post('/moderation-cases/$caseId/transition', {
      'status': _statusToWire(status),
      'notes': notes,
      'hide_content': hideContent,
    });
    return _toCase(body as Map<String, dynamic>);
  }

  @override
  Future<ModerationCase> appeal(
    String caseId,
    String appellantId,
    String reason,
  ) async {
    try {
      final body = await _post('/moderation-cases/$caseId/appeal', {
        'reason': reason,
      });
      return _toCase(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const ModerationFailure('Only decided cases can be appealed.');
      }
      rethrow;
    }
  }

  @override
  Future<ModerationAnalytics> analytics() async {
    final body =
        await _get('/moderation-cases/analytics') as Map<String, dynamic>;
    return ModerationAnalytics(
      totalReports: body['total_reports'] as int,
      openReports: body['open_reports'] as int,
      removedContent: body['removed_content'] as int,
      suspendedProviders: body['suspended_providers'] as int,
      repeatOffenders: (body['repeat_offenders'] as Map<String, dynamic>).map(
        (key, value) => MapEntry(key, value as int),
      ),
    );
  }

  @override
  Future<ModerationWarning> issueWarning({
    required String caseId,
    required String moderatorId,
    required String reason,
  }) async {
    try {
      final body = await _post('/moderation-cases/$caseId/warning', {
        'reason': reason,
      });
      return _toWarning(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const ModerationFailure(
          'Warnings can only be issued to providers or users.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<List<ModerationWarning>> warningsFor(
    ReportedEntityType entityType,
    String entityId,
  ) async {
    final body = await _get('/moderation-warnings', {
      'entity_type': _entityTypeToWire(entityType),
      'entity_id': entityId,
    });
    return (body as List<dynamic>)
        .map((item) => _toWarning(item as Map<String, dynamic>))
        .toList();
  }

  ModerationCase _toCase(Map<String, dynamic> json) => ModerationCase(
    id: json['id'] as String,
    reporterId: json['reporter_id'] as String,
    entityType: _entityTypeFromWire(json['entity_type'] as String),
    entityId: json['entity_id'] as String,
    reportType: _reportTypeFromWire(json['report_type'] as String),
    description: json['description'] as String,
    evidence: (json['evidence'] as List<dynamic>)
        .map(
          (item) => ModerationEvidence(
            location: (item as Map<String, dynamic>)['location'] as String,
            description: item['description'] as String,
          ),
        )
        .toList(),
    status: _statusFromWire(json['status'] as String),
    createdAt: DateTime.parse(json['created_at'] as String),
    history: (json['history'] as List<dynamic>)
        .map((item) => _toHistoryEntry(item as Map<String, dynamic>))
        .toList(),
    assignedModeratorId: json['assigned_moderator_id'] as String?,
    moderationNotes: json['moderation_notes'] as String?,
    temporarilyHidden: json['temporarily_hidden'] as bool,
    appealReason: json['appeal_reason'] as String?,
  );

  ModerationHistoryEntry _toHistoryEntry(Map<String, dynamic> json) =>
      ModerationHistoryEntry(
        status: _statusFromWire(json['status'] as String),
        actorId: json['actor_id'] as String,
        notes: json['notes'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  ModerationWarning _toWarning(Map<String, dynamic> json) => ModerationWarning(
    id: json['id'] as String,
    entityType: _entityTypeFromWire(json['entity_type'] as String),
    entityId: json['entity_id'] as String,
    reason: json['reason'] as String,
    issuedBy: json['issued_by'] as String,
    issuedAt: DateTime.parse(json['issued_at'] as String),
    caseId: json['case_id'] as String,
  );

  // ReportedEntityType's members are already flat lowercase words on both
  // sides - no translation needed, but kept as an explicit map for
  // consistency with the other two enums below (and so an unrecognized
  // value fails loudly rather than silently).
  static String _entityTypeToWire(ReportedEntityType type) => switch (type) {
    ReportedEntityType.opportunity => 'opportunity',
    ReportedEntityType.provider => 'provider',
    ReportedEntityType.user => 'user',
  };

  static ReportedEntityType _entityTypeFromWire(String value) =>
      switch (value) {
        'opportunity' => ReportedEntityType.opportunity,
        'provider' => ReportedEntityType.provider,
        'user' => ReportedEntityType.user,
        _ => throw LiveBackendException('Unknown reported entity type: $value'),
      };

  // Keep these two maps in sync with app/schemas/moderation.py's wire maps.
  static String _reportTypeToWire(ModerationReportType type) => switch (type) {
    ModerationReportType.scam => 'scam',
    ModerationReportType.incorrectDeadline => 'incorrectDeadline',
    ModerationReportType.brokenLink => 'brokenLink',
    ModerationReportType.duplicateListing => 'duplicateListing',
    ModerationReportType.misleadingContent => 'misleadingContent',
    ModerationReportType.inappropriateContent => 'inappropriateContent',
    ModerationReportType.outdatedContent => 'outdatedContent',
    ModerationReportType.harmfulContent => 'harmfulContent',
  };

  static ModerationReportType _reportTypeFromWire(String value) =>
      switch (value) {
        'scam' => ModerationReportType.scam,
        'incorrectDeadline' => ModerationReportType.incorrectDeadline,
        'brokenLink' => ModerationReportType.brokenLink,
        'duplicateListing' => ModerationReportType.duplicateListing,
        'misleadingContent' => ModerationReportType.misleadingContent,
        'inappropriateContent' => ModerationReportType.inappropriateContent,
        'outdatedContent' => ModerationReportType.outdatedContent,
        'harmfulContent' => ModerationReportType.harmfulContent,
        _ => throw LiveBackendException(
          'Unknown moderation report type: $value',
        ),
      };

  static String _statusToWire(ModerationStatus status) => switch (status) {
    ModerationStatus.submitted => 'submitted',
    ModerationStatus.underReview => 'underReview',
    ModerationStatus.evidenceRequired => 'evidenceRequired',
    ModerationStatus.escalated => 'escalated',
    ModerationStatus.resolved => 'resolved',
    ModerationStatus.rejected => 'rejected',
    ModerationStatus.contentCorrected => 'contentCorrected',
    ModerationStatus.contentRemoved => 'contentRemoved',
    ModerationStatus.providerSuspended => 'providerSuspended',
    ModerationStatus.closed => 'closed',
  };

  static ModerationStatus _statusFromWire(String value) => switch (value) {
    'submitted' => ModerationStatus.submitted,
    'underReview' => ModerationStatus.underReview,
    'evidenceRequired' => ModerationStatus.evidenceRequired,
    'escalated' => ModerationStatus.escalated,
    'resolved' => ModerationStatus.resolved,
    'rejected' => ModerationStatus.rejected,
    'contentCorrected' => ModerationStatus.contentCorrected,
    'contentRemoved' => ModerationStatus.contentRemoved,
    'providerSuspended' => ModerationStatus.providerSuspended,
    'closed' => ModerationStatus.closed,
    _ => throw LiveBackendException('Unknown moderation status: $value'),
  };

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
