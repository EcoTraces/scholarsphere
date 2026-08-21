import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../authentication/domain/user_account.dart';
import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/backup_recovery.dart';
import '../domain/backup_repository.dart';

/// Reads and writes real backup, recovery-test, and disaster-recovery data
/// from the ScholarSphere Python backend. Live replacement for
/// [DemoBackupRepository].
///
/// `actor` is accepted on every method for interface compatibility but
/// never sent: authorization is enforced server-side from the caller's own
/// verified auth token. [createBackup]/[verifyIntegrity] still simulate
/// the backup process itself (no real storage backend is integrated),
/// exactly as the demo did - only the record-keeping moved server-side.
class ApiBackupRepository implements BackupRepository {
  ApiBackupRepository({
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
  Future<BackupPolicy> policy() async {
    final body = await _get('/backup/policy');
    return _toPolicy(body as Map<String, dynamic>);
  }

  @override
  Future<void> savePolicy(UserAccount actor, BackupPolicy policy) async {
    try {
      await _put('/backup/policy', {
        'full_backup_interval_seconds': policy.fullBackupInterval.inSeconds,
        'transaction_log_interval_seconds':
            policy.transactionLogInterval.inSeconds,
        'retention_seconds': policy.retention.inSeconds,
        'monthly_restore_test': policy.monthlyRestoreTest,
        'encryption_required': policy.encryptionRequired,
        'separate_region_required': policy.separateRegionRequired,
        'recovery_point_objective_seconds':
            policy.recoveryPointObjective.inSeconds,
        'recovery_time_objective_seconds':
            policy.recoveryTimeObjective.inSeconds,
      });
    } on LiveBackendException catch (error) {
      if (error.statusCode == 422) {
        throw StateError('Recovery targets exceed the approved maximums.');
      }
      rethrow;
    }
  }

  @override
  Future<BackupRecord> createBackup(
    UserAccount actor,
    BackupType type, {
    required String region,
  }) async {
    final body = await _post('/backup/backups', {
      'type': _typeToWire(type),
      'region': region,
    });
    return _toRecord(body as Map<String, dynamic>);
  }

  @override
  Future<BackupRecord> verifyIntegrity(
    UserAccount actor,
    String backupId,
  ) async {
    try {
      final body = await _post('/backup/backups/$backupId/verify', const {});
      return _toRecord(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw StateError('Backup was not found.');
      }
      if (error.statusCode == 409) {
        throw StateError('Backup integrity verification failed.');
      }
      rethrow;
    }
  }

  @override
  Future<RecoveryTest> testRecovery(UserAccount actor, String backupId) async {
    try {
      final body = await _post(
        '/backup/backups/$backupId/test-recovery',
        const {},
      );
      final json = body as Map<String, dynamic>;
      return RecoveryTest(
        id: json['id'] as String,
        backupId: json['backup_id'] as String,
        status: RecoveryStatus.values.firstWhere(
          (value) => value.name == json['status'],
        ),
        startedAt: DateTime.parse(json['started_at'] as String),
        completedAt: DateTime.parse(json['completed_at'] as String),
        integrityValid: json['integrity_valid'] as bool,
        duration: Duration(seconds: json['duration_seconds'] as int),
        notes: json['notes'] as String,
      );
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw StateError('Backup was not found.');
      }
      if (error.statusCode == 409) {
        throw StateError('Backup integrity verification failed.');
      }
      rethrow;
    }
  }

  @override
  Future<List<BackupRecord>> backups(UserAccount actor) async {
    final body = await _get('/backup/backups');
    return (body as List<dynamic>)
        .map((item) => _toRecord(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<int> enforceRetention(UserAccount actor) async {
    final body = await _post('/backup/retention/enforce', const {});
    return (body as Map<String, dynamic>)['removed'] as int;
  }

  @override
  Future<DisasterRecoveryPlan> disasterRecoveryPlan(UserAccount actor) async {
    final body = await _get('/backup/disaster-recovery-plan');
    final json = body as Map<String, dynamic>;
    return DisasterRecoveryPlan(
      version: json['version'] as int,
      primaryRegion: json['primary_region'] as String,
      recoveryRegion: json['recovery_region'] as String,
      restorationSteps: (json['restoration_steps'] as List<dynamic>)
          .cast<String>(),
      emergencyContacts: (json['emergency_contacts'] as List<dynamic>)
          .cast<String>(),
      businessContinuitySteps:
          (json['business_continuity_steps'] as List<dynamic>).cast<String>(),
      lastReviewedAt: DateTime.parse(json['last_reviewed_at'] as String),
    );
  }

  BackupPolicy _toPolicy(Map<String, dynamic> json) => BackupPolicy(
    fullBackupInterval: Duration(
      seconds: json['full_backup_interval_seconds'] as int,
    ),
    transactionLogInterval: Duration(
      seconds: json['transaction_log_interval_seconds'] as int,
    ),
    retention: Duration(seconds: json['retention_seconds'] as int),
    monthlyRestoreTest: json['monthly_restore_test'] as bool,
    encryptionRequired: json['encryption_required'] as bool,
    separateRegionRequired: json['separate_region_required'] as bool,
    recoveryPointObjective: Duration(
      seconds: json['recovery_point_objective_seconds'] as int,
    ),
    recoveryTimeObjective: Duration(
      seconds: json['recovery_time_objective_seconds'] as int,
    ),
  );

  BackupRecord _toRecord(Map<String, dynamic> json) => BackupRecord(
    id: json['id'] as String,
    type: _typeFromWire(json['type'] as String),
    status: BackupStatus.values.firstWhere(
      (value) => value.name == json['status'],
    ),
    storageLocation: json['storage_location'] as String,
    region: json['region'] as String,
    encrypted: json['encrypted'] as bool,
    createdAt: DateTime.parse(json['created_at'] as String),
    completedAt: json['completed_at'] == null
        ? null
        : DateTime.parse(json['completed_at'] as String),
    expiresAt: json['expires_at'] == null
        ? null
        : DateTime.parse(json['expires_at'] as String),
    sizeBytes: json['size_bytes'] as int,
    checksum: json['checksum'] as String,
    failureReason: json['failure_reason'] as String?,
  );

  // Keep in sync with app/models/backup.py's enum wire values.
  static String _typeToWire(BackupType type) => type.name;

  static BackupType _typeFromWire(String value) => BackupType.values
      .firstWhere(
        (type) => type.name == value,
        orElse: () => throw LiveBackendException('Unknown backup type: $value'),
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
