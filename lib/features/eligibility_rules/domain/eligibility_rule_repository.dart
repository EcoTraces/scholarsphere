import 'eligibility_rule.dart';

abstract class EligibilityRuleRepository {
  Future<EligibilityRuleSet> createVersion({
    required String opportunityId,
    required List<EligibilityRule> rules,
    required String createdBy,
  });
  Future<EligibilityRuleSet?> getActive(String opportunityId);
  Future<List<EligibilityRuleSet>> getVersions(String opportunityId);
  Future<void> saveOverride(String opportunityId, EligibilityOverride override);
  Future<List<EligibilityOverride>> getOverrides(String opportunityId);
}

class EligibilityRuleFailure implements Exception {
  const EligibilityRuleFailure(this.message);
  final String message;
}
