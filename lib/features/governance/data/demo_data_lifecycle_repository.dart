import '../../audit/domain/audit_record.dart';
import '../../audit/domain/audit_repository.dart';
import '../../authentication/domain/user_account.dart';
import '../domain/data_lifecycle.dart';
import '../domain/data_lifecycle_repository.dart';

class DemoDataLifecycleRepository implements DataLifecycleRepository {
  DemoDataLifecycleRepository({
    this.auditRepository,
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now;

  final AuditRepository? auditRepository;
  final DateTime Function() _clock;
  final Map<RetainedEntityType, RetentionRule> _rules = {};
  final Map<String, LifecycleRecord> _records = {};
  final List<LegalHold> _holds = [];

  String _key(RetainedEntityType type, String id) => '${type.name}:$id';

  @override
  Future<void> saveRule(UserAccount actor, RetentionRule rule) async {
    _authorize(actor);
    if (rule.activeDuration.isNegative ||
        rule.archiveDuration.isNegative ||
        (rule.entityType == RetainedEntityType.auditLog &&
            rule.activeDuration < const Duration(days: 365))) {
      throw StateError('Retention policy is invalid.');
    }
    _rules[rule.entityType] = rule;
  }

  @override
  Future<List<RetentionRule>> rules(UserAccount actor) async {
    _authorize(actor);
    return _rules.values.toList();
  }

  @override
  Future<LifecycleRecord> register(LifecycleRecord record) async {
    _records[_key(record.entityType, record.entityId)] = record;
    return record;
  }

  @override
  Future<LifecycleRecord> softDelete(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  ) async {
    _authorize(actor);
    final record = _require(type, entityId);
    _ensureNoHold(type, entityId);
    final updated = record.copyWith(
      status: LifecycleStatus.softDeleted,
      updatedAt: _clock(),
    );
    _records[_key(type, entityId)] = updated;
    await _audit(actor, 'soft_deleted', type, entityId);
    return updated;
  }

  @override
  Future<LifecycleRecord> permanentlyDelete(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  ) async {
    _authorize(actor);
    final record = _require(type, entityId);
    _ensureNoHold(type, entityId);
    final now = _clock();
    final rule = _rules[type];
    final updated = record.copyWith(
      status: LifecycleStatus.permanentlyDeleted,
      updatedAt: now,
      deletedAt: now,
      backupDeletionDueAt: now.add(
        rule?.deleteFromBackupsAfter ?? const Duration(days: 35),
      ),
      deletionVerification:
          'active-storage-absent:${now.microsecondsSinceEpoch}',
    );
    _records[_key(type, entityId)] = updated;
    await _audit(actor, 'permanently_deleted', type, entityId);
    return updated;
  }

  @override
  Future<LifecycleRecord> restore(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  ) async {
    _authorize(actor);
    final record = _require(type, entityId);
    if (record.status == LifecycleStatus.permanentlyDeleted) {
      throw StateError('Permanently deleted data cannot be restored.');
    }
    final updated = record.copyWith(
      status: LifecycleStatus.restored,
      updatedAt: _clock(),
    );
    _records[_key(type, entityId)] = updated;
    await _audit(actor, 'archive_restored', type, entityId);
    return updated;
  }

  @override
  Future<LegalHold> placeLegalHold(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
    String reason,
  ) async {
    _authorize(actor);
    _require(type, entityId);
    final hold = LegalHold(
      id: 'hold-${_clock().microsecondsSinceEpoch}',
      entityType: type,
      entityId: entityId,
      reason: reason,
      placedBy: actor.id,
      placedAt: _clock(),
    );
    _holds.add(hold);
    await _audit(actor, 'legal_hold_placed', type, entityId);
    return hold;
  }

  @override
  Future<CleanupReport> runCleanup(UserAccount actor) async {
    _authorize(actor);
    final now = _clock();
    var archived = 0;
    var deleted = 0;
    var held = 0;
    for (final entry in _records.entries.toList()) {
      final record = entry.value;
      final rule = _rules[record.entityType];
      if (rule == null || record.status == LifecycleStatus.permanentlyDeleted) {
        continue;
      }
      if (_hasHold(record.entityType, record.entityId)) {
        held++;
        continue;
      }
      final age = now.difference(record.createdAt);
      if (record.status == LifecycleStatus.active &&
          age >= rule.activeDuration) {
        _records[entry.key] = record.copyWith(
          status: LifecycleStatus.archived,
          archivedAt: now,
          updatedAt: now,
        );
        archived++;
      } else if (record.status == LifecycleStatus.archived &&
          record.archivedAt != null &&
          now.difference(record.archivedAt!) >= rule.archiveDuration) {
        await permanentlyDelete(actor, record.entityType, record.entityId);
        deleted++;
      }
    }
    return CleanupReport(
      archived: archived,
      permanentlyDeleted: deleted,
      skippedLegalHolds: held,
      completedAt: now,
    );
  }

  @override
  Future<bool> verifyDeletion(
    UserAccount actor,
    RetainedEntityType type,
    String entityId,
  ) async {
    _authorize(actor);
    final record = _require(type, entityId);
    return record.status == LifecycleStatus.permanentlyDeleted &&
        record.deletionVerification != null;
  }

  LifecycleRecord _require(RetainedEntityType type, String id) {
    final value = _records[_key(type, id)];
    if (value == null) throw StateError('Lifecycle record was not found.');
    return value;
  }

  bool _hasHold(RetainedEntityType type, String id) => _holds.any(
    (hold) => hold.active && hold.entityType == type && hold.entityId == id,
  );

  void _ensureNoHold(RetainedEntityType type, String id) {
    if (_hasHold(type, id)) {
      throw StateError('This record is protected by a legal hold.');
    }
  }

  void _authorize(UserAccount actor) {
    if (!{
      UserRole.administrator,
      UserRole.securityAdministrator,
      UserRole.superAdministrator,
    }.contains(actor.role)) {
      throw StateError('Retention access requires an administrator.');
    }
  }

  Future<void> _audit(
    UserAccount actor,
    String action,
    RetainedEntityType type,
    String id,
  ) =>
      auditRepository?.append(
        actorId: actor.id,
        actorRole: actor.role.name,
        action: AuditAction.accountDeleted,
        entityType: type.name,
        entityId: id,
        newValue: action,
        result: AuditResult.success,
        correlationId: '$action-${type.name}-$id',
      ) ??
      Future.value();
}
