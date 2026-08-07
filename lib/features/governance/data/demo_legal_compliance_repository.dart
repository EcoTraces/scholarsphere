import '../domain/legal_compliance.dart';
import '../domain/legal_compliance_repository.dart';

class DemoLegalComplianceRepository implements LegalComplianceRepository {
  final Map<LegalPolicyType, List<LegalPolicy>> _policies = {};
  final List<PolicyAcceptance> _acceptances = [];
  final Map<String, LegalRequest> _requests = {};
  final Map<String, ComplianceRecord> _compliance = {};

  @override
  Future<LegalPolicy> publish(LegalPolicy policy) async {
    final versions = _policies.putIfAbsent(policy.type, () => []);
    if (versions.any((item) => item.version == policy.version)) {
      throw StateError('This policy version already exists.');
    }
    versions.add(policy);
    return policy;
  }

  @override
  Future<LegalPolicy?> current(LegalPolicyType type) async {
    final versions = _policies[type] ?? const [];
    return versions.isEmpty ? null : versions.last;
  }

  @override
  Future<List<LegalPolicy>> versions(LegalPolicyType type) async =>
      List.unmodifiable(_policies[type] ?? const []);

  @override
  Future<void> accept(PolicyAcceptance acceptance) async {
    final policy = await current(
      _policies.entries
          .firstWhere(
            (entry) =>
                entry.value.any((item) => item.id == acceptance.policyId),
            orElse: () => throw StateError('Policy was not found.'),
          )
          .key,
    );
    if (policy == null || policy.version != acceptance.policyVersion) {
      throw StateError('Only the current policy version can be accepted.');
    }
    _acceptances.removeWhere(
      (item) =>
          item.userId == acceptance.userId &&
          item.policyId == acceptance.policyId,
    );
    _acceptances.add(acceptance);
  }

  @override
  Future<bool> hasAcceptedCurrent(String userId, LegalPolicyType type) async {
    final policy = await current(type);
    if (policy == null || !policy.requiresAcceptance) return true;
    return _acceptances.any(
      (item) =>
          item.userId == userId &&
          item.policyId == policy.id &&
          item.policyVersion == policy.version,
    );
  }

  @override
  Future<List<String>> pendingPolicyNotifications(String userId) async {
    final pending = <String>[];
    for (final type in LegalPolicyType.values) {
      final policy = await current(type);
      if (policy != null &&
          policy.materialChange &&
          !await hasAcceptedCurrent(userId, type)) {
        pending.add('${policy.title} ${policy.version} requires review.');
      }
    }
    return pending;
  }

  @override
  Future<LegalRequest> submitLegalRequest(LegalRequest request) async {
    if (request.description.trim().isEmpty) {
      throw StateError('A legal request description is required.');
    }
    _requests[request.id] = request;
    return request;
  }

  @override
  Future<List<LegalRequest>> legalRequests() async => _requests.values.toList();

  @override
  Future<void> saveComplianceRecord(ComplianceRecord record) async {
    _compliance[record.id] = record;
  }

  @override
  Future<List<ComplianceRecord>> complianceRecords() async =>
      _compliance.values.toList();
}
