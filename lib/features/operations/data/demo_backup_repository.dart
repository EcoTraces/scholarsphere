import '../../audit/domain/audit_record.dart';
import '../../audit/domain/audit_repository.dart';
import '../../authentication/domain/user_account.dart';
import '../domain/backup_recovery.dart';
import '../domain/backup_repository.dart';

class DemoBackupRepository implements BackupRepository {
  DemoBackupRepository({this.auditRepository, DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final AuditRepository? auditRepository;
  final DateTime Function() _clock;
  BackupPolicy _policy = const BackupPolicy();
  final Map<String, BackupRecord> _backups = {};

  @override
  Future<BackupPolicy> policy() async => _policy;

  @override
  Future<void> savePolicy(UserAccount actor, BackupPolicy policy) async {
    _authorize(actor);
    if (policy.recoveryPointObjective > const Duration(minutes: 15) ||
        policy.recoveryTimeObjective > const Duration(hours: 4)) {
      throw StateError('Recovery targets exceed the approved maximums.');
    }
    _policy = policy;
  }

  @override
  Future<BackupRecord> createBackup(
    UserAccount actor,
    BackupType type, {
    required String region,
  }) async {
    _authorize(actor);
    final now = _clock();
    final record = BackupRecord(
      id: 'backup-${now.microsecondsSinceEpoch}-${_backups.length}',
      type: type,
      status: BackupStatus.completed,
      storageLocation: 'encrypted://backup-vault/${type.name}/$now',
      region: region,
      encrypted: true,
      createdAt: now,
      completedAt: now,
      expiresAt: now.add(_policy.retention),
      sizeBytes: type == BackupType.transactionLog ? 1024 : 1024 * 1024,
      checksum: 'checksum-${now.microsecondsSinceEpoch}',
    );
    _backups[record.id] = record;
    await _audit(actor, 'backup_created', record.id);
    return record;
  }

  @override
  Future<BackupRecord> verifyIntegrity(
    UserAccount actor,
    String backupId,
  ) async {
    _authorize(actor);
    final record = _require(backupId);
    if (!record.encrypted || record.checksum.isEmpty) {
      throw StateError('Backup integrity verification failed.');
    }
    final verified = record.copyWith(status: BackupStatus.verified);
    _backups[backupId] = verified;
    await _audit(actor, 'backup_verified', backupId);
    return verified;
  }

  @override
  Future<RecoveryTest> testRecovery(UserAccount actor, String backupId) async {
    final verified = await verifyIntegrity(actor, backupId);
    final started = _clock();
    final completed = started.add(const Duration(minutes: 20));
    final test = RecoveryTest(
      id: 'recovery-test-${started.microsecondsSinceEpoch}',
      backupId: backupId,
      status: RecoveryStatus.completed,
      startedAt: started,
      completedAt: completed,
      integrityValid: verified.status == BackupStatus.verified,
      duration: completed.difference(started),
      notes: 'Isolated restoration test completed within the RTO.',
    );
    await _audit(actor, 'recovery_test_completed', backupId);
    return test;
  }

  @override
  Future<List<BackupRecord>> backups(UserAccount actor) async {
    _authorize(actor);
    return _backups.values.toList();
  }

  @override
  Future<int> enforceRetention(UserAccount actor) async {
    _authorize(actor);
    final now = _clock();
    final before = _backups.length;
    _backups.removeWhere(
      (_, backup) =>
          backup.expiresAt != null && backup.expiresAt!.isBefore(now),
    );
    return before - _backups.length;
  }

  @override
  Future<DisasterRecoveryPlan> disasterRecoveryPlan(UserAccount actor) async {
    _authorize(actor);
    return DisasterRecoveryPlan(
      version: 1,
      primaryRegion: 'primary-region',
      recoveryRegion: 'separate-recovery-region',
      restorationSteps: const [
        'Declare the incident and freeze writes.',
        'Verify the latest encrypted backup and transaction logs.',
        'Restore data in the recovery region.',
        'Validate security, integrity, and application health.',
        'Approve traffic failover and notify stakeholders.',
      ],
      emergencyContacts: const ['security-lead', 'operations-lead'],
      businessContinuitySteps: const [
        'Enable the public status page.',
        'Use read-only opportunity access where safe.',
        'Prioritize authentication and application tracking restoration.',
      ],
      lastReviewedAt: _clock(),
    );
  }

  BackupRecord _require(String id) {
    final value = _backups[id];
    if (value == null) throw StateError('Backup was not found.');
    return value;
  }

  void _authorize(UserAccount actor) {
    if (!{
      UserRole.securityAdministrator,
      UserRole.superAdministrator,
    }.contains(actor.role)) {
      throw StateError('Backup access requires a security administrator.');
    }
  }

  Future<void> _audit(UserAccount actor, String action, String entityId) =>
      auditRepository?.append(
        actorId: actor.id,
        actorRole: actor.role.name,
        action: AuditAction.administrativeAction,
        entityType: 'backup',
        entityId: entityId,
        newValue: action,
        result: AuditResult.success,
        correlationId: '$action-$entityId',
      ) ??
      Future.value();
}
