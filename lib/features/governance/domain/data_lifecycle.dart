enum RetainedEntityType {
  opportunity,
  userAccount,
  document,
  notification,
  auditLog,
  supportTicket,
  providerRecord,
}

enum LifecycleStatus {
  active,
  softDeleted,
  archived,
  pendingPermanentDeletion,
  permanentlyDeleted,
  restored,
}

class RetentionRule {
  const RetentionRule({
    required this.entityType,
    required this.activeDuration,
    required this.archiveDuration,
    required this.deleteFromBackupsAfter,
    required this.archiveExpiredRecords,
    required this.retainRejectedForFraudPrevention,
  });
  final RetainedEntityType entityType;
  final Duration activeDuration;
  final Duration archiveDuration;
  final Duration deleteFromBackupsAfter;
  final bool archiveExpiredRecords;
  final bool retainRejectedForFraudPrevention;
}

class LegalHold {
  const LegalHold({
    required this.id,
    required this.entityType,
    required this.entityId,
    required this.reason,
    required this.placedBy,
    required this.placedAt,
    this.releasedAt,
  });
  final String id;
  final RetainedEntityType entityType;
  final String entityId;
  final String reason;
  final String placedBy;
  final DateTime placedAt;
  final DateTime? releasedAt;
  bool get active => releasedAt == null;
}

class LifecycleRecord {
  const LifecycleRecord({
    required this.id,
    required this.entityType,
    required this.entityId,
    required this.ownerId,
    required this.status,
    required this.containsPersonalData,
    required this.createdAt,
    required this.updatedAt,
    this.archivedAt,
    this.deletedAt,
    this.backupDeletionDueAt,
    this.deletionVerification,
  });
  final String id;
  final RetainedEntityType entityType;
  final String entityId;
  final String? ownerId;
  final LifecycleStatus status;
  final bool containsPersonalData;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? archivedAt;
  final DateTime? deletedAt;
  final DateTime? backupDeletionDueAt;
  final String? deletionVerification;

  LifecycleRecord copyWith({
    LifecycleStatus? status,
    DateTime? updatedAt,
    DateTime? archivedAt,
    DateTime? deletedAt,
    DateTime? backupDeletionDueAt,
    String? deletionVerification,
  }) => LifecycleRecord(
    id: id,
    entityType: entityType,
    entityId: entityId,
    ownerId: ownerId,
    status: status ?? this.status,
    containsPersonalData: containsPersonalData,
    createdAt: createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    archivedAt: archivedAt ?? this.archivedAt,
    deletedAt: deletedAt ?? this.deletedAt,
    backupDeletionDueAt: backupDeletionDueAt ?? this.backupDeletionDueAt,
    deletionVerification: deletionVerification ?? this.deletionVerification,
  );
}

class CleanupReport {
  const CleanupReport({
    required this.archived,
    required this.permanentlyDeleted,
    required this.skippedLegalHolds,
    required this.completedAt,
  });
  final int archived;
  final int permanentlyDeleted;
  final int skippedLegalHolds;
  final DateTime completedAt;
}
