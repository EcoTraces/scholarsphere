import '../../authentication/domain/user_account.dart';
import 'backup_recovery.dart';

abstract class BackupRepository {
  Future<BackupPolicy> policy();
  Future<void> savePolicy(UserAccount actor, BackupPolicy policy);
  Future<BackupRecord> createBackup(
    UserAccount actor,
    BackupType type, {
    required String region,
  });
  Future<BackupRecord> verifyIntegrity(UserAccount actor, String backupId);
  Future<RecoveryTest> testRecovery(UserAccount actor, String backupId);
  Future<List<BackupRecord>> backups(UserAccount actor);
  Future<int> enforceRetention(UserAccount actor);
  Future<DisasterRecoveryPlan> disasterRecoveryPlan(UserAccount actor);
}
