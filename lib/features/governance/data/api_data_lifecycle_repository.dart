import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../authentication/domain/user_account.dart';
import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/data_lifecycle.dart';
import '../domain/data_lifecycle_repository.dart';

/// Reads and writes real data-retention, legal-hold, and lifecycle records
/// from the ScholarSphere Python backend. Live replacement for
/// [DemoDataLifecycleRepository].
///
/// The `actor` parameter is accepted on every method for interface
/// compatibility but never sent to the server: the caller's identity for
/// authorization and audit logging is always taken from their own
/// verified auth token server-side, never trusted from the client.
class ApiDataLifecycleRepository implements DataLifecycleRepository {
  ApiDataLifecycleRepository({
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
  Future<void> saveRule(UserAccount actor, RetentionRule rule) async {
    try {
      await _put(
        '/data-lifecycle/rules/${_entityTypeToWire(rule.entityType)}',
        {
          'active_duration_seconds': rule.activeDuration.inSeconds,
          'archive_duration_seconds': rule.archiveDuration.inSeconds,
          'delete_from_backups_after_seconds':
              rule.deleteFromBackupsAfter.inSeconds,
          'archive_expired_records': rule.archiveExpiredRecords,
          'retain_rejected_for_fraud_prevention':
              rule.retainRejectedForFraudPrevention,
        },
      );
    } on LiveBackendException catch (error) {
      if (error.statusCode == 422) {
        throw StateError('Retention policy is invalid.');
      }
      rethrow;
    }
  }

  @override
  Future<List<RetentionRule>> rules(UserAccount actor) async {
    final body = await _get('/data-lifecycle/rules');
    return (body as List<dynamic>)
        .map((item) => _toRule(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<LifecycleRecord> register(LifecycleRecord record) async {
    final body = await _post('/data-lifecycle/records', {
      'entity_type': _entityTypeToWire(record.entityType),
      'entity_id': record.entityId,
      'owner_id': record.ownerId,
      'status': _statusToWire(record.status),
      'contains_personal_data': record.containsPersonalData,
    });
    return _toRecord(body as Map<String, dynamic>);
  }

  @override
  Future<LifecycleRecord> softDelete(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  ) async {
    try {
      final body = await _post(
        '/data-lifecycle/records/${_entityTypeToWire(type)}/$entityId/soft-delete',
        const {},
      );
      return _toRecord(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw StateError('This record is protected by a legal hold.');
      }
      rethrow;
    }
  }

  @override
  Future<LifecycleRecord> permanentlyDelete(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  ) async {
    try {
      final body = await _post(
        '/data-lifecycle/records/${_entityTypeToWire(type)}/$entityId/permanently-delete',
        const {},
      );
      return _toRecord(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw StateError('This record is protected by a legal hold.');
      }
      rethrow;
    }
  }

  @override
  Future<LifecycleRecord> restore(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  ) async {
    try {
      final body = await _post(
        '/data-lifecycle/records/${_entityTypeToWire(type)}/$entityId/restore',
        const {},
      );
      return _toRecord(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw StateError('Permanently deleted data cannot be restored.');
      }
      rethrow;
    }
  }

  @override
  Future<LegalHold> placeLegalHold(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
    String reason,
  ) async {
    final body = await _post(
      '/data-lifecycle/legal-holds/${_entityTypeToWire(type)}/$entityId',
      {'reason': reason},
    );
    return _toHold(body as Map<String, dynamic>);
  }

  @override
  Future<CleanupReport> runCleanup(UserAccount actor) async {
    final body = await _post('/data-lifecycle/cleanup', const {});
    final json = body as Map<String, dynamic>;
    return CleanupReport(
      archived: json['archived'] as int,
      permanentlyDeleted: json['permanently_deleted'] as int,
      skippedLegalHolds: json['skipped_legal_holds'] as int,
      completedAt: DateTime.parse(json['completed_at'] as String),
    );
  }

  @override
  Future<bool> verifyDeletion(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  ) async {
    final body = await _get(
      '/data-lifecycle/records/${_entityTypeToWire(type)}/$entityId/verify-deletion',
    );
    return body as bool;
  }

  RetentionRule _toRule(Map<String, dynamic> json) => RetentionRule(
    entityType: _entityTypeFromWire(json['entity_type'] as String),
    activeDuration: Duration(seconds: json['active_duration_seconds'] as int),
    archiveDuration: Duration(seconds: json['archive_duration_seconds'] as int),
    deleteFromBackupsAfter: Duration(
      seconds: json['delete_from_backups_after_seconds'] as int,
    ),
    archiveExpiredRecords: json['archive_expired_records'] as bool,
    retainRejectedForFraudPrevention:
        json['retain_rejected_for_fraud_prevention'] as bool,
  );

  LifecycleRecord _toRecord(Map<String, dynamic> json) => LifecycleRecord(
    id: '${json['entity_type']}:${json['entity_id']}',
    entityType: _entityTypeFromWire(json['entity_type'] as String),
    entityId: json['entity_id'] as String,
    ownerId: json['owner_id'] as String?,
    status: _statusFromWire(json['status'] as String),
    containsPersonalData: json['contains_personal_data'] as bool,
    createdAt: DateTime.parse(json['created_at'] as String),
    updatedAt: DateTime.parse(json['updated_at'] as String),
    archivedAt: json['archived_at'] == null
        ? null
        : DateTime.parse(json['archived_at'] as String),
    deletedAt: json['deleted_at'] == null
        ? null
        : DateTime.parse(json['deleted_at'] as String),
    backupDeletionDueAt: json['backup_deletion_due_at'] == null
        ? null
        : DateTime.parse(json['backup_deletion_due_at'] as String),
    deletionVerification: json['deletion_verification'] as String?,
  );

  LegalHold _toHold(Map<String, dynamic> json) => LegalHold(
    id: json['id'] as String,
    entityType: _entityTypeFromWire(json['entity_type'] as String),
    entityId: json['entity_id'] as String,
    reason: json['reason'] as String,
    placedBy: json['placed_by'] as String,
    placedAt: DateTime.parse(json['placed_at'] as String),
    releasedAt: json['released_at'] == null
        ? null
        : DateTime.parse(json['released_at'] as String),
  );

  // Keep in sync with app/models/data_lifecycle.py's enum wire values.
  static String _entityTypeToWire(RetainedEntityType type) => type.name;

  static RetainedEntityType _entityTypeFromWire(String value) =>
      RetainedEntityType.values.firstWhere(
        (type) => type.name == value,
        orElse: () =>
            throw LiveBackendException('Unknown retained entity type: $value'),
      );

  static String _statusToWire(LifecycleStatus status) => status.name;

  static LifecycleStatus _statusFromWire(String value) =>
      LifecycleStatus.values.firstWhere(
        (status) => status.name == value,
        orElse: () =>
            throw LiveBackendException('Unknown lifecycle status: $value'),
      );

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
