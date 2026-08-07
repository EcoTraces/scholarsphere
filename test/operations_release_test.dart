import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/authentication/domain/user_account.dart';
import 'package:scholarsphere/features/operations/data/demo_backup_repository.dart';
import 'package:scholarsphere/features/operations/data/demo_observability_repository.dart';
import 'package:scholarsphere/features/operations/data/demo_release_repository.dart';
import 'package:scholarsphere/features/operations/data/demo_system_configuration_repository.dart';
import 'package:scholarsphere/features/operations/domain/backup_recovery.dart';
import 'package:scholarsphere/features/operations/domain/observability.dart';
import 'package:scholarsphere/features/operations/domain/quality_release.dart';
import 'package:scholarsphere/features/operations/domain/release_repository.dart';

void main() {
  test(
    'configuration updates are versioned and rollback creates history',
    () async {
      final repository = DemoSystemConfigurationRepository(
        clock: () => DateTime.utc(2026, 7, 29),
      );
      final initial = await repository.current();
      final updated = await repository.update(
        _admin('admin-1'),
        initial.copyWith(platformName: 'ScholarSphere Test'),
        'Testing configuration change',
      );
      final rolledBack = await repository.rollback(
        _admin('admin-1'),
        initial.version,
        'Restore production name',
      );

      expect(updated.version, 2);
      expect(rolledBack.version, 3);
      expect(rolledBack.platformName, 'ScholarSphere');
      expect(await repository.history(_admin('admin-1')), hasLength(3));
    },
  );

  test('metrics trigger alerts and performance reports', () async {
    final repository = DemoObservabilityRepository(
      clock: () => DateTime.utc(2026, 7, 29),
    );
    await repository.saveAlertRule(
      const AlertRule(
        id: 'errors',
        metricName: 'request.error_rate',
        threshold: 0.05,
        comparison: 'greaterThan',
        severity: LogLevel.critical,
        escalationTarget: 'on-call',
        enabled: true,
      ),
    );
    await repository.metric(
      MetricPoint(
        name: 'request.error_rate',
        value: .12,
        unit: 'ratio',
        timestamp: DateTime.utc(2026, 7, 29),
        labels: const {'service': 'api'},
      ),
    );
    expect((await repository.incidents()).single.severity, LogLevel.critical);
    expect(
      (await repository.performanceReport()).metrics['request.error_rate'],
      .12,
    );
  });

  test(
    'backup operations enforce access, encryption, and recovery targets',
    () async {
      final repository = DemoBackupRepository(
        clock: () => DateTime.utc(2026, 7, 29),
      );
      await expectLater(
        repository.createBackup(
          _admin('admin-1'),
          BackupType.fullDatabase,
          region: 'recovery-region',
        ),
        throwsA(isA<StateError>()),
      );
      final security = _admin(
        'security-1',
        role: UserRole.securityAdministrator,
      );
      final backup = await repository.createBackup(
        security,
        BackupType.fullDatabase,
        region: 'recovery-region',
      );
      final verified = await repository.verifyIntegrity(security, backup.id);
      final recovery = await repository.testRecovery(security, backup.id);

      expect(verified.status, BackupStatus.verified);
      expect(verified.encrypted, isTrue);
      expect(recovery.integrityValid, isTrue);
      expect(recovery.duration, lessThan(const Duration(hours: 4)));
      expect(
        (await repository.policy()).recoveryPointObjective,
        const Duration(minutes: 15),
      );
    },
  );

  test(
    'quality gates and second-person approval control production release',
    () async {
      final repository = DemoReleaseRepository(
        clock: () => DateTime.utc(2026, 7, 29),
      );
      final artifact = ReleaseArtifact(
        version: '2.0.0',
        commitSha: 'abc123',
        imageReference: 'registry/scholarsphere@sha256:test',
        releaseNotes: 'Operational controls release.',
        createdAt: DateTime.utc(2026, 7, 29),
        migrationIds: const [],
      );
      await expectLater(
        repository.createDeployment(
          _admin('admin-1'),
          artifact,
          DeploymentEnvironment.production,
          DeploymentStrategy.blueGreen,
        ),
        throwsA(isA<ReleaseFailure>()),
      );
      await repository.saveQualityReport(
        QualityReport(
          releaseVersion: artifact.version,
          checks: [
            QualityCheck(
              id: 'regression',
              category: TestCategory.regression,
              outcome: TestOutcome.passed,
              critical: true,
              executedAt: DateTime.utc(2026, 7, 29),
              details: 'All automated tests passed.',
            ),
          ],
          coveragePercent: 85,
          mandatoryEligibilityCoveragePercent: 100,
          securityFindings: const [],
          generatedAt: DateTime.utc(2026, 7, 29),
        ),
      );
      final deployment = await repository.createDeployment(
        _admin('admin-1'),
        artifact,
        DeploymentEnvironment.production,
        DeploymentStrategy.blueGreen,
      );
      await expectLater(
        repository.approve(_admin('admin-1'), deployment.id),
        throwsA(isA<ReleaseFailure>()),
      );
      final approved = await repository.approve(
        _admin('admin-2'),
        deployment.id,
      );
      final deployed = await repository.deploy(_admin('admin-1'), approved.id);
      final rolledBack = await repository.rollback(
        _admin('admin-2'),
        deployed.id,
      );

      expect(deployed.status, DeploymentStatus.completed);
      expect(rolledBack.status, DeploymentStatus.rolledBack);
    },
  );
}

UserAccount _admin(String id, {UserRole role = UserRole.administrator}) =>
    UserAccount(
      id: id,
      fullName: 'Administrator',
      email: '$id@scholarsphere.test',
      role: role,
      status: AccountStatus.active,
      emailVerified: true,
      twoFactorEnabled: true,
    );
