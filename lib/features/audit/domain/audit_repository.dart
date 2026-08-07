import '../../authentication/domain/user_account.dart';
import 'audit_record.dart';

abstract class AuditRepository {
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
  });
  Future<List<AuditRecord>> search(UserRole requesterRole, AuditQuery query);
  Future<String> exportCsv(UserRole requesterRole, AuditQuery query);
  Future<int> enforceRetention();
  Future<bool> verifyIntegrity();
  Future<AuditRetentionPolicy> getRetentionPolicy();
  Future<void> setRetentionPolicy(
    UserRole requesterRole,
    AuditRetentionPolicy policy,
  );
}

class AuditFailure implements Exception {
  const AuditFailure(this.message);
  final String message;
}
