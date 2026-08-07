enum BackupType { fullDatabase, incremental, transactionLog, fileStorage }

enum BackupStatus { scheduled, running, completed, failed, verified, expired }

enum RecoveryStatus { requested, approved, running, completed, failed }

class BackupPolicy {
  const BackupPolicy({
    this.fullBackupInterval = const Duration(days: 1),
    this.transactionLogInterval = const Duration(minutes: 15),
    this.retention = const Duration(days: 35),
    this.monthlyRestoreTest = true,
    this.encryptionRequired = true,
    this.separateRegionRequired = true,
    this.recoveryPointObjective = const Duration(minutes: 15),
    this.recoveryTimeObjective = const Duration(hours: 4),
  });
  final Duration fullBackupInterval;
  final Duration transactionLogInterval;
  final Duration retention;
  final bool monthlyRestoreTest;
  final bool encryptionRequired;
  final bool separateRegionRequired;
  final Duration recoveryPointObjective;
  final Duration recoveryTimeObjective;
}

class BackupRecord {
  const BackupRecord({
    required this.id,
    required this.type,
    required this.status,
    required this.storageLocation,
    required this.region,
    required this.encrypted,
    required this.createdAt,
    required this.sizeBytes,
    required this.checksum,
    this.completedAt,
    this.expiresAt,
    this.failureReason,
  });
  final String id;
  final BackupType type;
  final BackupStatus status;
  final String storageLocation;
  final String region;
  final bool encrypted;
  final DateTime createdAt;
  final DateTime? completedAt;
  final DateTime? expiresAt;
  final int sizeBytes;
  final String checksum;
  final String? failureReason;

  BackupRecord copyWith({BackupStatus? status, DateTime? completedAt}) =>
      BackupRecord(
        id: id,
        type: type,
        status: status ?? this.status,
        storageLocation: storageLocation,
        region: region,
        encrypted: encrypted,
        createdAt: createdAt,
        completedAt: completedAt ?? this.completedAt,
        expiresAt: expiresAt,
        sizeBytes: sizeBytes,
        checksum: checksum,
        failureReason: failureReason,
      );
}

class RecoveryTest {
  const RecoveryTest({
    required this.id,
    required this.backupId,
    required this.status,
    required this.startedAt,
    required this.completedAt,
    required this.integrityValid,
    required this.duration,
    required this.notes,
  });
  final String id;
  final String backupId;
  final RecoveryStatus status;
  final DateTime startedAt;
  final DateTime completedAt;
  final bool integrityValid;
  final Duration duration;
  final String notes;
}

class DisasterRecoveryPlan {
  const DisasterRecoveryPlan({
    required this.version,
    required this.primaryRegion,
    required this.recoveryRegion,
    required this.restorationSteps,
    required this.emergencyContacts,
    required this.businessContinuitySteps,
    required this.lastReviewedAt,
  });
  final int version;
  final String primaryRegion;
  final String recoveryRegion;
  final List<String> restorationSteps;
  final List<String> emergencyContacts;
  final List<String> businessContinuitySteps;
  final DateTime lastReviewedAt;
}
