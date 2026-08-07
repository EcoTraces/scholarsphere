import '../../audit/domain/audit_record.dart';
import '../../audit/domain/audit_repository.dart';
import '../../authentication/domain/user_account.dart';
import '../domain/system_configuration.dart';
import '../domain/system_configuration_repository.dart';

class DemoSystemConfigurationRepository
    implements SystemConfigurationRepository {
  DemoSystemConfigurationRepository({
    this.auditRepository,
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now {
    _history.add(PlatformConfiguration.defaults());
  }

  final AuditRepository? auditRepository;
  final DateTime Function() _clock;
  final List<PlatformConfiguration> _history = [];

  @override
  Future<PlatformConfiguration> current() async => _history.last;

  @override
  Future<PlatformConfiguration> update(
    UserAccount actor,
    PlatformConfiguration configuration,
    String reason,
  ) async {
    _authorize(actor);
    _validate(configuration);
    final previous = _history.last;
    final updated = configuration.copyWith(
      version: previous.version + 1,
      updatedAt: _clock(),
      updatedBy: actor.id,
      changeReason: reason,
    );
    _history.add(updated);
    await auditRepository?.append(
      actorId: actor.id,
      actorRole: actor.role.name,
      action: AuditAction.administrativeAction,
      entityType: 'platform_configuration',
      entityId: 'global',
      previousValue: 'version=${previous.version}',
      newValue: 'version=${updated.version}',
      result: AuditResult.success,
      correlationId: 'config-${updated.version}',
    );
    return updated;
  }

  @override
  Future<List<PlatformConfiguration>> history(UserAccount actor) async {
    _authorize(actor);
    return List.unmodifiable(_history.reversed);
  }

  @override
  Future<PlatformConfiguration> rollback(
    UserAccount actor,
    int targetVersion,
    String reason,
  ) async {
    _authorize(actor);
    final target = _history.where((item) => item.version == targetVersion);
    if (target.isEmpty) {
      throw const ConfigurationFailure('Configuration version was not found.');
    }
    return update(actor, target.first, 'Rollback: $reason');
  }

  void _authorize(UserAccount actor) {
    if (!{
      UserRole.administrator,
      UserRole.securityAdministrator,
      UserRole.superAdministrator,
    }.contains(actor.role)) {
      throw const ConfigurationFailure(
        'Configuration access is restricted to administrators.',
      );
    }
  }

  void _validate(PlatformConfiguration value) {
    if (value.platformName.trim().isEmpty ||
        value.verificationExpirationDays < 1 ||
        value.maximumFileSizeBytes < 1024 ||
        value.supportedLanguages.isEmpty) {
      throw const ConfigurationFailure('Configuration values are invalid.');
    }
    if (value.featureFlags[FeatureFlag.providerSelfPublication] == true &&
        value.securityPolicy['mfaForAdministrators'] != true) {
      throw const ConfigurationFailure(
        'Provider self-publication requires the stronger security policy.',
      );
    }
  }
}
