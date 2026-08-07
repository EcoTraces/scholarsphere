import '../../authentication/domain/user_account.dart';
import 'data_lifecycle.dart';

abstract class DataLifecycleRepository {
  Future<void> saveRule(UserAccount actor, RetentionRule rule);
  Future<List<RetentionRule>> rules(UserAccount actor);
  Future<LifecycleRecord> register(LifecycleRecord record);
  Future<LifecycleRecord> softDelete(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  );
  Future<LifecycleRecord> permanentlyDelete(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  );
  Future<LifecycleRecord> restore(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  );
  Future<LegalHold> placeLegalHold(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
    String reason,
  );
  Future<CleanupReport> runCleanup(UserAccount actor);
  Future<bool> verifyDeletion(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  );
}
