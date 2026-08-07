import '../../authentication/domain/user_account.dart';
import 'system_configuration.dart';

abstract class SystemConfigurationRepository {
  Future<PlatformConfiguration> current();
  Future<PlatformConfiguration> update(
    UserAccount actor,
    PlatformConfiguration configuration,
    String reason,
  );
  Future<List<PlatformConfiguration>> history(UserAccount actor);
  Future<PlatformConfiguration> rollback(
    UserAccount actor,
    int targetVersion,
    String reason,
  );
}

class ConfigurationFailure implements Exception {
  const ConfigurationFailure(this.message);
  final String message;
}
