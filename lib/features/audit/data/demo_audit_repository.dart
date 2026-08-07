import 'dart:convert';

import '../../authentication/domain/user_account.dart';
import '../domain/audit_record.dart';
import '../domain/audit_repository.dart';

class DemoAuditRepository implements AuditRepository {
  DemoAuditRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final List<AuditRecord> _records = [];
  String _chainAnchor = 'GENESIS';
  AuditRetentionPolicy _retention = const AuditRetentionPolicy();

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
  }) async {
    final timestamp = _clock();
    final previousHash = _records.isEmpty
        ? _chainAnchor
        : _records.last.integrityHash;
    final maskedPrevious = _mask(previousValue);
    final maskedNew = _mask(newValue);
    final payload = [
      previousHash,
      actorId,
      actorRole,
      action.name,
      entityType,
      entityId,
      maskedPrevious,
      maskedNew,
      timestamp.toUtc().toIso8601String(),
      result.name,
      correlationId,
    ].join('|');
    final record = AuditRecord(
      id: 'audit-${timestamp.microsecondsSinceEpoch}-${_records.length}',
      actorId: actorId,
      actorRole: actorRole,
      action: action,
      entityType: entityType,
      entityId: entityId,
      previousValue: maskedPrevious,
      newValue: maskedNew,
      ipAddress: _maskIp(ipAddress),
      deviceInformation: deviceInformation,
      locationInformation: locationInformation,
      timestamp: timestamp,
      result: result,
      failureReason: _mask(failureReason),
      correlationId: correlationId,
      integrityHash: _hash(payload),
    );
    _records.add(record);
    return record;
  }

  @override
  Future<List<AuditRecord>> search(
    UserRole requesterRole,
    AuditQuery query,
  ) async {
    _authorize(requesterRole);
    return _records.where((record) {
      return (query.actorId == null || record.actorId == query.actorId) &&
          (query.action == null || record.action == query.action) &&
          (query.entityType == null || record.entityType == query.entityType) &&
          (query.entityId == null || record.entityId == query.entityId) &&
          (query.result == null || record.result == query.result) &&
          (query.from == null || !record.timestamp.isBefore(query.from!)) &&
          (query.to == null || !record.timestamp.isAfter(query.to!));
    }).toList();
  }

  @override
  Future<String> exportCsv(UserRole requesterRole, AuditQuery query) async {
    final records = await search(requesterRole, query);
    final lines = [
      'audit_id,actor_id,actor_role,action,entity_type,entity_id,timestamp,result,correlation_id',
      ...records.map(
        (record) => [
          record.id,
          record.actorId,
          record.actorRole,
          record.action.name,
          record.entityType,
          record.entityId,
          record.timestamp.toUtc().toIso8601String(),
          record.result.name,
          record.correlationId,
        ].map(_csv).join(','),
      ),
    ];
    return lines.join('\n');
  }

  @override
  Future<int> enforceRetention() async {
    final cutoff = _clock().subtract(Duration(days: _retention.retentionDays));
    final before = _records.length;
    final removed = _records.where(
      (record) => record.timestamp.isBefore(cutoff),
    );
    if (removed.isNotEmpty) _chainAnchor = removed.last.integrityHash;
    _records.removeWhere((record) => record.timestamp.isBefore(cutoff));
    return before - _records.length;
  }

  @override
  Future<bool> verifyIntegrity() async {
    var previousHash = _chainAnchor;
    for (final record in _records) {
      final payload = [
        previousHash,
        record.actorId,
        record.actorRole,
        record.action.name,
        record.entityType,
        record.entityId,
        record.previousValue,
        record.newValue,
        record.timestamp.toUtc().toIso8601String(),
        record.result.name,
        record.correlationId,
      ].join('|');
      if (_hash(payload) != record.integrityHash) return false;
      previousHash = record.integrityHash;
    }
    return true;
  }

  @override
  Future<AuditRetentionPolicy> getRetentionPolicy() async => _retention;

  @override
  Future<void> setRetentionPolicy(
    UserRole requesterRole,
    AuditRetentionPolicy policy,
  ) async {
    _authorize(requesterRole);
    if (policy.retentionDays < 365) {
      throw const AuditFailure('Audit retention cannot be less than 365 days.');
    }
    _retention = policy;
  }

  void _authorize(UserRole role) {
    if (!{
      UserRole.administrator,
      UserRole.securityAdministrator,
      UserRole.superAdministrator,
    }.contains(role)) {
      throw const AuditFailure('Audit access is restricted to administrators.');
    }
  }

  String? _mask(String? value) {
    if (value == null) return null;
    return value
        .replaceAll(RegExp(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}'), '[masked-email]')
        .replaceAllMapped(
          RegExp(r'(password|token|secret)=[^,\s}]+', caseSensitive: false),
          (match) => '${match.group(1)}=***',
        )
        .replaceAll(RegExp(r'\b\d{12,19}\b'), '[masked-number]');
  }

  String _maskIp(String value) {
    final parts = value.split('.');
    return parts.length == 4 ? '${parts[0]}.${parts[1]}.*.*' : value;
  }

  String _hash(String value) {
    final bytes = utf8.encode(value);
    var hash = BigInt.parse('cbf29ce484222325', radix: 16);
    final prime = BigInt.parse('100000001b3', radix: 16);
    final mask = BigInt.parse('ffffffffffffffff', radix: 16);
    for (final byte in bytes) {
      hash ^= BigInt.from(byte);
      hash = (hash * prime) & mask;
    }
    return hash.toRadixString(16).padLeft(16, '0');
  }

  String _csv(String value) => '"${value.replaceAll('"', '""')}"';
}
