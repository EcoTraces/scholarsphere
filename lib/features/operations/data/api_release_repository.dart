import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../authentication/domain/user_account.dart';
import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/quality_release.dart';
import '../domain/release_repository.dart';

/// Reads and writes real quality-report and deployment data from the
/// ScholarSphere Python backend. Live replacement for
/// [DemoReleaseRepository].
///
/// `actor` is accepted on every method for interface compatibility but
/// never sent: authorization and the recorded actor identity are always
/// taken from the caller's own verified auth token server-side.
class ApiReleaseRepository implements ReleaseRepository {
  ApiReleaseRepository({
    String? baseUrl,
    http.Client? client,
    firebase.FirebaseAuth? auth,
  }) : baseUrl = baseUrl ?? _defaultBaseUrl,
       _client = client ?? http.Client(),
       _authOverride = auth {
    if (kReleaseMode) {
      TransportSecurityPolicy.requireHttps(Uri.parse(this.baseUrl));
    }
  }

  static const _defaultBaseUrl = String.fromEnvironment(
    'SCHOLARSPHERE_API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  final String baseUrl;
  final http.Client _client;
  final firebase.FirebaseAuth? _authOverride;

  firebase.FirebaseAuth get _auth =>
      _authOverride ?? firebase.FirebaseAuth.instance;

  @override
  Future<void> saveQualityReport(QualityReport report) async {
    await _put(
      '/release/quality-reports/${Uri.encodeComponent(report.releaseVersion)}',
      {
        'checks': report.checks.map(_checkToWire).toList(),
        'coverage_percent': report.coveragePercent,
        'mandatory_eligibility_coverage_percent':
            report.mandatoryEligibilityCoveragePercent,
        'security_findings': report.securityFindings
            .map(_findingToWire)
            .toList(),
      },
    );
  }

  @override
  Future<QualityReport?> qualityReport(String version) async {
    final body = await _get(
      '/release/quality-reports/${Uri.encodeComponent(version)}',
    );
    if (body == null) return null;
    return _toReport(body as Map<String, dynamic>);
  }

  @override
  Future<DeploymentRecord> createDeployment(
    UserAccount actor,
    ReleaseArtifact artifact,
    DeploymentEnvironment environment,
    DeploymentStrategy strategy,
  ) async {
    try {
      final body = await _post('/release/deployments', {
        'artifact': _artifactToWire(artifact),
        'environment': environment.name,
        'strategy': strategy.name,
      });
      return _toDeployment(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const ReleaseFailure(
          'Deployment is blocked until all quality gates pass.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<DeploymentRecord> approve(
    UserAccount actor,
    String deploymentId,
  ) async {
    try {
      final body = await _post(
        '/release/deployments/$deploymentId/approve',
        const {},
      );
      return _toDeployment(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const ReleaseFailure('Deployment was not found.');
      }
      if (error.statusCode == 409) {
        throw const ReleaseFailure(
          'Production approval requires a second administrator.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<DeploymentRecord> deploy(
    UserAccount actor,
    String deploymentId,
  ) async {
    try {
      final body = await _post(
        '/release/deployments/$deploymentId/deploy',
        const {},
      );
      return _toDeployment(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const ReleaseFailure('Deployment was not found.');
      }
      if (error.statusCode == 409) {
        throw const ReleaseFailure('Deployment is not approved.');
      }
      rethrow;
    }
  }

  @override
  Future<DeploymentRecord> rollback(
    UserAccount actor,
    String deploymentId,
  ) async {
    try {
      final body = await _post(
        '/release/deployments/$deploymentId/rollback',
        const {},
      );
      return _toDeployment(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const ReleaseFailure('Deployment was not found.');
      }
      if (error.statusCode == 409) {
        throw const ReleaseFailure('Only completed deployments can roll back.');
      }
      rethrow;
    }
  }

  @override
  Future<List<DeploymentRecord>> history(UserAccount actor) async {
    final body = await _get('/release/deployments');
    return (body as List<dynamic>)
        .map((item) => _toDeployment(item as Map<String, dynamic>))
        .toList();
  }

  Map<String, dynamic> _checkToWire(QualityCheck check) => {
    'id': check.id,
    'category': check.category.name,
    'outcome': check.outcome.name,
    'critical': check.critical,
    'executed_at': check.executedAt.toUtc().toIso8601String(),
    'details': check.details,
  };

  Map<String, dynamic> _findingToWire(SecurityFinding finding) => {
    'id': finding.id,
    'severity': finding.severity.name,
    'resolved': finding.resolved,
    'summary': finding.summary,
  };

  Map<String, dynamic> _artifactToWire(ReleaseArtifact artifact) => {
    'version': artifact.version,
    'commit_sha': artifact.commitSha,
    'image_reference': artifact.imageReference,
    'release_notes': artifact.releaseNotes,
    'created_at': artifact.createdAt.toUtc().toIso8601String(),
    'migration_ids': artifact.migrationIds,
  };

  QualityReport _toReport(Map<String, dynamic> json) => QualityReport(
    releaseVersion: json['release_version'] as String,
    checks: (json['checks'] as List<dynamic>)
        .map((item) => _checkFromWire(item as Map<String, dynamic>))
        .toList(),
    coveragePercent: (json['coverage_percent'] as num).toDouble(),
    mandatoryEligibilityCoveragePercent:
        (json['mandatory_eligibility_coverage_percent'] as num).toDouble(),
    securityFindings: (json['security_findings'] as List<dynamic>)
        .map((item) => _findingFromWire(item as Map<String, dynamic>))
        .toList(),
    generatedAt: DateTime.parse(json['generated_at'] as String),
  );

  QualityCheck _checkFromWire(Map<String, dynamic> json) => QualityCheck(
    id: json['id'] as String,
    category: TestCategory.values.firstWhere(
      (value) => value.name == json['category'],
    ),
    outcome: TestOutcome.values.firstWhere(
      (value) => value.name == json['outcome'],
    ),
    critical: json['critical'] as bool,
    executedAt: DateTime.parse(json['executed_at'] as String),
    details: json['details'] as String? ?? '',
  );

  SecurityFinding _findingFromWire(Map<String, dynamic> json) =>
      SecurityFinding(
        id: json['id'] as String,
        severity: Severity.values.firstWhere(
          (value) => value.name == json['severity'],
        ),
        resolved: json['resolved'] as bool,
        summary: json['summary'] as String? ?? '',
      );

  DeploymentRecord _toDeployment(Map<String, dynamic> json) =>
      DeploymentRecord(
        id: json['id'] as String,
        artifact: _artifactFromWire(json['artifact'] as Map<String, dynamic>),
        environment: DeploymentEnvironment.values.firstWhere(
          (value) => value.name == json['environment'],
        ),
        strategy: DeploymentStrategy.values.firstWhere(
          (value) => value.name == json['strategy'],
        ),
        status: DeploymentStatus.values.firstWhere(
          (value) => value.name == json['status'],
        ),
        createdBy: json['created_by'] as String,
        approvedBy: json['approved_by'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String),
        previousDeploymentId: json['previous_deployment_id'] as String?,
        history: (json['history'] as List<dynamic>).cast<String>(),
      );

  ReleaseArtifact _artifactFromWire(Map<String, dynamic> json) =>
      ReleaseArtifact(
        version: json['version'] as String,
        commitSha: json['commit_sha'] as String,
        imageReference: json['image_reference'] as String,
        releaseNotes: json['release_notes'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
        migrationIds: (json['migration_ids'] as List<dynamic>).cast<String>(),
      );

  Future<dynamic> _get(String path) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(() => _client.get(uri, headers: headers));
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.post(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _put(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.put(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _handle(Future<http.Response> Function() request) async {
    late final http.Response response;
    try {
      response = await request();
    } on Exception catch (error) {
      throw LiveBackendException(
        'Could not reach the ScholarSphere backend: $error',
      );
    }
    if (response.statusCode == 401) {
      throw const LiveBackendException(
        'Sign-in expired. Sign in again.',
        statusCode: 401,
      );
    }
    if (response.statusCode >= 400) {
      throw LiveBackendException(
        'The ScholarSphere backend returned an error.',
        statusCode: response.statusCode,
      );
    }
    if (response.body.isEmpty) return null;
    return jsonDecode(response.body);
  }

  Future<Map<String, String>> _headers() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const LiveBackendException('Sign in first.', statusCode: 401);
    }
    final token = await user.getIdToken();
    return {
      'Authorization': 'Bearer $token',
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
  }

  void dispose() => _client.close();
}
