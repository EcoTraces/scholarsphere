import '../../audit/domain/audit_record.dart';
import '../../audit/domain/audit_repository.dart';
import '../../authentication/domain/user_account.dart';
import '../domain/quality_release.dart';
import '../domain/release_repository.dart';

class DemoReleaseRepository implements ReleaseRepository {
  DemoReleaseRepository({this.auditRepository, DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final AuditRepository? auditRepository;
  final DateTime Function() _clock;
  final Map<String, QualityReport> _quality = {};
  final Map<String, DeploymentRecord> _deployments = {};

  @override
  Future<void> saveQualityReport(QualityReport report) async {
    _quality[report.releaseVersion] = report;
  }

  @override
  Future<QualityReport?> qualityReport(String version) async =>
      _quality[version];

  @override
  Future<DeploymentRecord> createDeployment(
    UserAccount actor,
    ReleaseArtifact artifact,
    DeploymentEnvironment environment,
    DeploymentStrategy strategy,
  ) async {
    _authorize(actor);
    final report = _quality[artifact.version];
    if (report == null || !report.productionReady) {
      throw const ReleaseFailure(
        'Deployment is blocked until all quality gates pass.',
      );
    }
    final now = _clock();
    final latest = _deployments.values
        .where(
          (deployment) =>
              deployment.environment == environment &&
              deployment.status == DeploymentStatus.completed,
        )
        .lastOrNull;
    final deployment = DeploymentRecord(
      id: 'deployment-${now.microsecondsSinceEpoch}',
      artifact: artifact,
      environment: environment,
      strategy: strategy,
      status: environment == DeploymentEnvironment.production
          ? DeploymentStatus.awaitingApproval
          : DeploymentStatus.approved,
      createdBy: actor.id,
      createdAt: now,
      previousDeploymentId: latest?.id,
      history: ['Deployment created by ${actor.id}.'],
    );
    _deployments[deployment.id] = deployment;
    return deployment;
  }

  @override
  Future<DeploymentRecord> approve(
    UserAccount actor,
    String deploymentId,
  ) async {
    _authorize(actor);
    final current = _require(deploymentId);
    if (current.createdBy == actor.id &&
        current.environment == DeploymentEnvironment.production) {
      throw const ReleaseFailure(
        'Production approval requires a second administrator.',
      );
    }
    return _save(
      current.copyWith(
        status: DeploymentStatus.approved,
        approvedBy: actor.id,
        history: [...current.history, 'Approved by ${actor.id}.'],
      ),
      actor,
      'deployment_approved',
    );
  }

  @override
  Future<DeploymentRecord> deploy(
    UserAccount actor,
    String deploymentId,
  ) async {
    _authorize(actor);
    final current = _require(deploymentId);
    if (current.status != DeploymentStatus.approved) {
      throw const ReleaseFailure('Deployment is not approved.');
    }
    return _save(
      current.copyWith(
        status: DeploymentStatus.completed,
        history: [
          ...current.history,
          '${current.strategy.name} deployment completed.',
        ],
      ),
      actor,
      'deployment_completed',
    );
  }

  @override
  Future<DeploymentRecord> rollback(
    UserAccount actor,
    String deploymentId,
  ) async {
    _authorize(actor);
    final current = _require(deploymentId);
    if (current.status != DeploymentStatus.completed) {
      throw const ReleaseFailure('Only completed deployments can roll back.');
    }
    return _save(
      current.copyWith(
        status: DeploymentStatus.rolledBack,
        history: [...current.history, 'Rolled back by ${actor.id}.'],
      ),
      actor,
      'deployment_rolled_back',
    );
  }

  @override
  Future<List<DeploymentRecord>> history(UserAccount actor) async {
    _authorize(actor);
    return _deployments.values.toList().reversed.toList();
  }

  DeploymentRecord _require(String id) {
    final value = _deployments[id];
    if (value == null) throw const ReleaseFailure('Deployment was not found.');
    return value;
  }

  Future<DeploymentRecord> _save(
    DeploymentRecord value,
    UserAccount actor,
    String action,
  ) async {
    _deployments[value.id] = value;
    await auditRepository?.append(
      actorId: actor.id,
      actorRole: actor.role.name,
      action: AuditAction.administrativeAction,
      entityType: 'deployment',
      entityId: value.id,
      newValue: action,
      result: AuditResult.success,
      correlationId: '$action-${value.id}',
    );
    return value;
  }

  void _authorize(UserAccount actor) {
    if (!{
      UserRole.administrator,
      UserRole.superAdministrator,
    }.contains(actor.role)) {
      throw const ReleaseFailure('Release access requires an administrator.');
    }
  }
}
