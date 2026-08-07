import '../domain/eligibility_rule.dart';
import '../domain/eligibility_rule_repository.dart';

class DemoEligibilityRuleRepository implements EligibilityRuleRepository {
  DemoEligibilityRuleRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final Map<String, List<EligibilityRuleSet>> _versions = {};
  final Map<String, List<EligibilityOverride>> _overrides = {};

  @override
  Future<EligibilityRuleSet> createVersion({
    required String opportunityId,
    required List<EligibilityRule> rules,
    required String createdBy,
  }) async {
    if (rules.isEmpty) {
      throw const EligibilityRuleFailure('At least one rule is required.');
    }
    if (rules.any((rule) => rule.weight < 0 || rule.weight > 100)) {
      throw const EligibilityRuleFailure('Rule weights must be from 0 to 100.');
    }
    final existing = _versions.putIfAbsent(opportunityId, () => []);
    for (var index = 0; index < existing.length; index++) {
      existing[index] = existing[index].copyWith(isActive: false);
    }
    final set = EligibilityRuleSet(
      id: 'rules-$opportunityId-${existing.length + 1}',
      opportunityId: opportunityId,
      version: existing.length + 1,
      rules: List.unmodifiable(rules),
      createdAt: _clock(),
      createdBy: createdBy,
      isActive: true,
    );
    existing.add(set);
    return set;
  }

  @override
  Future<EligibilityRuleSet?> getActive(String opportunityId) async {
    final matches = _versions[opportunityId] ?? const [];
    final active = matches.where((set) => set.isActive);
    return active.isEmpty ? null : active.last;
  }

  @override
  Future<List<EligibilityRuleSet>> getVersions(String opportunityId) async =>
      List.unmodifiable(_versions[opportunityId] ?? const []);

  @override
  Future<void> saveOverride(
    String opportunityId,
    EligibilityOverride override,
  ) async {
    _overrides.putIfAbsent(opportunityId, () => []).add(override);
  }

  @override
  Future<List<EligibilityOverride>> getOverrides(String opportunityId) async =>
      List.unmodifiable(_overrides[opportunityId] ?? const []);
}
