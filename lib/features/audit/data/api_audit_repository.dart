import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../authentication/domain/user_account.dart';
import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/audit_record.dart';
import '../domain/audit_repository.dart';

/// Reads real audit records from the ScholarSphere Python backend. Live
/// replacement for [DemoAuditRepository].
///
/// [append] is intentionally unimplemented: on the live backend, audit
/// writes happen as an internal call from the writing route (e.g. system
/// configuration, backup, release, data lifecycle) into the same database
/// transaction, not as a separate network round-trip from the client -
/// mirroring the demo's in-process `auditRepository?.append(...)` calls
/// from those other Demo repositories. Once every one of those repositories
/// is backend-backed, nothing in the Flutter app calls [append] anymore,
/// so it throws rather than silently no-op-ing or fabricating a fake
/// unpersisted record that could mislead a future caller.
///
/// [search]/[exportCsv]/[setRetentionPolicy]'s `requesterRole` parameter is
/// accepted for interface compatibility but never sent: authorization is
/// enforced server-side from the caller's own verified auth token.
class ApiAuditRepository implements AuditRepository {
  ApiAuditRepository({
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
  Future<AuditRecord> append({
    required String actorId,
    required String actorRole,
    required AuditAction action,
    required String entityType,
    required String entityId,
    required AuditResult result,
    required String correlationId,
    String? previousValue,
    String? newValue,
    String ipAddress = '',
    String deviceInformation = '',
    String locationInformation = '',
    String? failureReason,
  }) {
    throw UnsupportedError(
      'ApiAuditRepository.append is unreachable on the live backend: audit '
      'writes happen server-side, in-process, from the route performing '
      'the audited action.',
    );
  }

  @override
  Future<List<AuditRecord>> search(
    UserRole requesterRole,
    AuditQuery query,
  ) async {
    final body = await _get('/audit/records', _queryParameters(query));
    return (body as List<dynamic>)
        .map((item) => _toRecord(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<String> exportCsv(UserRole requesterRole, AuditQuery query) async {
    final body = await _get('/audit/records/export', _queryParameters(query));
    return (body as Map<String, dynamic>)['csv'] as String;
  }

  @override
  Future<int> enforceRetention() async {
    final body = await _post('/audit/retention/enforce', const {});
    return (body as Map<String, dynamic>)['removed'] as int;
  }

  @override
  Future<bool> verifyIntegrity() async {
    final body = await _get('/audit/integrity', const {});
    return body as bool;
  }

  @override
  Future<AuditRetentionPolicy> getRetentionPolicy() async {
    final body = await _get('/audit/retention-policy', const {});
    return AuditRetentionPolicy(
      retentionDays: (body as Map<String, dynamic>)['retention_days'] as int,
    );
  }

  @override
  Future<void> setRetentionPolicy(
    UserRole requesterRole,
    AuditRetentionPolicy policy,
  ) async {
    try {
      await _put('/audit/retention-policy', {
        'retention_days': policy.retentionDays,
      });
    } on LiveBackendException catch (error) {
      if (error.statusCode == 422) {
        throw const AuditFailure(
          'Audit retention cannot be less than 365 days.',
        );
      }
      rethrow;
    }
  }

  Map<String, String> _queryParameters(AuditQuery query) => {
    if (query.actorId != null) 'actor_id': query.actorId!,
    if (query.action != null) 'action': query.action!.name,
    if (query.entityType != null) 'entity_type': query.entityType!,
    if (query.entityId != null) 'entity_id': query.entityId!,
    if (query.result != null) 'result': query.result!.name,
    if (query.from != null) 'from': query.from!.toUtc().toIso8601String(),
    if (query.to != null) 'to': query.to!.toUtc().toIso8601String(),
  };

  AuditRecord _toRecord(Map<String, dynamic> json) => AuditRecord(
    id: json['id'] as String,
    actorId: json['actor_id'] as String,
    actorRole: json['actor_role'] as String,
    action: AuditAction.values.firstWhere(
      (value) => value.name == json['action'],
      orElse: () =>
          throw LiveBackendException('Unknown audit action: ${json['action']}'),
    ),
    entityType: json['entity_type'] as String,
    entityId: json['entity_id'] as String,
    previousValue: json['previous_value'] as String?,
    newValue: json['new_value'] as String?,
    ipAddress: json['ip_address'] as String,
    deviceInformation: json['device_information'] as String,
    locationInformation: json['location_information'] as String,
    timestamp: DateTime.parse(json['timestamp'] as String),
    result: AuditResult.values.firstWhere(
      (value) => value.name == json['result'],
      orElse: () =>
          throw LiveBackendException('Unknown audit result: ${json['result']}'),
    ),
    failureReason: json['failure_reason'] as String?,
    correlationId: json['correlation_id'] as String,
    integrityHash: json['integrity_hash'] as String,
  );

  Future<dynamic> _get(String path, Map<String, String> query) async {
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

  Future<dynamic> _put(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.put(uri, headers: headers, body: jsonEncode(body)),
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
