enum AuditResult { success, failure, denied }

enum AuditAction {
  login,
  logout,
  failedLogin,
  profileChanged,
  roleChanged,
  permissionChanged,
  opportunityChanged,
  verificationDecision,
  documentAccessed,
  providerAction,
  administrativeAction,
  securityEvent,
  dataExported,
  accountDeleted,
  apiRequest,
}

class AuditRecord {
  const AuditRecord({
    required this.id,
    required this.actorId,
    required this.actorRole,
    required this.action,
    required this.entityType,
    required this.entityId,
    required this.previousValue,
    required this.newValue,
    required this.ipAddress,
    required this.deviceInformation,
    required this.locationInformation,
    required this.timestamp,
    required this.result,
    required this.correlationId,
    required this.integrityHash,
    this.failureReason,
  });

  final String id;
  final String actorId;
  final String actorRole;
  final AuditAction action;
  final String entityType;
  final String entityId;
  final String? previousValue;
  final String? newValue;
  final String ipAddress;
  final String deviceInformation;
  final String locationInformation;
  final DateTime timestamp;
  final AuditResult result;
  final String? failureReason;
  final String correlationId;
  final String integrityHash;
}

class AuditQuery {
  const AuditQuery({
    this.actorId,
    this.action,
    this.entityType,
    this.entityId,
    this.result,
    this.from,
    this.to,
  });
  final String? actorId;
  final AuditAction? action;
  final String? entityType;
  final String? entityId;
  final AuditResult? result;
  final DateTime? from;
  final DateTime? to;
}

class AuditRetentionPolicy {
  const AuditRetentionPolicy({this.retentionDays = 2555});
  final int retentionDays;
}
