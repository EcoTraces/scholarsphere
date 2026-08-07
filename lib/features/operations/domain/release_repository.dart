import '../../authentication/domain/user_account.dart';
import 'quality_release.dart';

abstract class ReleaseRepository {
  Future<void> saveQualityReport(QualityReport report);
  Future<QualityReport?> qualityReport(String version);
  Future<DeploymentRecord> createDeployment(
    UserAccount actor,
    ReleaseArtifact artifact,
    DeploymentEnvironment environment,
    DeploymentStrategy strategy,
  );
  Future<DeploymentRecord> approve(UserAccount actor, String deploymentId);
  Future<DeploymentRecord> deploy(UserAccount actor, String deploymentId);
  Future<DeploymentRecord> rollback(UserAccount actor, String deploymentId);
  Future<List<DeploymentRecord>> history(UserAccount actor);
}

class ReleaseFailure implements Exception {
  const ReleaseFailure(this.message);
  final String message;
}
