enum TestCategory {
  unit,
  integration,
  api,
  endToEnd,
  userInterface,
  mobile,
  browserCompatibility,
  database,
  eligibilityRules,
  recommendations,
  notifications,
  security,
  penetration,
  performance,
  load,
  stress,
  accessibility,
  localization,
  backupRestoration,
  userAcceptance,
  regression,
  dataMigration,
}

enum TestOutcome { passed, failed, skipped }

enum Severity { low, medium, high, critical }

class QualityCheck {
  const QualityCheck({
    required this.id,
    required this.category,
    required this.outcome,
    required this.critical,
    required this.executedAt,
    required this.details,
  });
  final String id;
  final TestCategory category;
  final TestOutcome outcome;
  final bool critical;
  final DateTime executedAt;
  final String details;
}

class SecurityFinding {
  const SecurityFinding({
    required this.id,
    required this.severity,
    required this.resolved,
    required this.summary,
  });
  final String id;
  final Severity severity;
  final bool resolved;
  final String summary;
}

class QualityReport {
  const QualityReport({
    required this.releaseVersion,
    required this.checks,
    required this.coveragePercent,
    required this.mandatoryEligibilityCoveragePercent,
    required this.securityFindings,
    required this.generatedAt,
  });
  final String releaseVersion;
  final List<QualityCheck> checks;
  final double coveragePercent;
  final double mandatoryEligibilityCoveragePercent;
  final List<SecurityFinding> securityFindings;
  final DateTime generatedAt;

  bool get productionReady =>
      coveragePercent >= 80 &&
      mandatoryEligibilityCoveragePercent == 100 &&
      !checks.any(
        (check) => check.critical && check.outcome != TestOutcome.passed,
      ) &&
      !securityFindings.any(
        (finding) => finding.severity == Severity.critical && !finding.resolved,
      );
}

enum DeploymentEnvironment { development, testing, staging, production }

enum DeploymentStrategy { standard, blueGreen, canary }

enum DeploymentStatus {
  draft,
  awaitingApproval,
  approved,
  deploying,
  completed,
  failed,
  rolledBack,
}

class ReleaseArtifact {
  const ReleaseArtifact({
    required this.version,
    required this.commitSha,
    required this.imageReference,
    required this.releaseNotes,
    required this.createdAt,
    required this.migrationIds,
  });
  final String version;
  final String commitSha;
  final String imageReference;
  final String releaseNotes;
  final DateTime createdAt;
  final List<String> migrationIds;
}

class DeploymentRecord {
  const DeploymentRecord({
    required this.id,
    required this.artifact,
    required this.environment,
    required this.strategy,
    required this.status,
    required this.createdBy,
    required this.createdAt,
    required this.history,
    this.approvedBy,
    this.previousDeploymentId,
  });
  final String id;
  final ReleaseArtifact artifact;
  final DeploymentEnvironment environment;
  final DeploymentStrategy strategy;
  final DeploymentStatus status;
  final String createdBy;
  final String? approvedBy;
  final DateTime createdAt;
  final String? previousDeploymentId;
  final List<String> history;

  DeploymentRecord copyWith({
    DeploymentStatus? status,
    String? approvedBy,
    List<String>? history,
  }) => DeploymentRecord(
    id: id,
    artifact: artifact,
    environment: environment,
    strategy: strategy,
    status: status ?? this.status,
    createdBy: createdBy,
    approvedBy: approvedBy ?? this.approvedBy,
    createdAt: createdAt,
    previousDeploymentId: previousDeploymentId,
    history: history ?? this.history,
  );
}
