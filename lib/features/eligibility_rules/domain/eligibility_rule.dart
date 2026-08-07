enum EligibilityRuleType {
  mandatory,
  preferred,
  optional,
  conditional,
  disqualifying,
  informational,
  unknownOrUnverified,
}

enum EligibilityAttribute {
  nationality,
  countryOfResidence,
  academicLevel,
  gpaOrClassification,
  age,
  languageTest,
  workExperienceYears,
  graduationYear,
  fieldOfStudy,
  gender,
  disabilityCategory,
  employmentStatus,
}

enum EligibilityOperator {
  equals,
  oneOf,
  contains,
  minimum,
  maximum,
  between,
  present,
}

class EligibilityRule {
  const EligibilityRule({
    required this.id,
    required this.label,
    required this.type,
    required this.attribute,
    required this.operator,
    required this.values,
    required this.weight,
    required this.officialSource,
    this.conditionRuleId,
    this.notes,
  });

  final String id;
  final String label;
  final EligibilityRuleType type;
  final EligibilityAttribute attribute;
  final EligibilityOperator operator;
  final List<String> values;
  final int weight;
  final bool officialSource;
  final String? conditionRuleId;
  final String? notes;
}

class EligibilityRuleSet {
  const EligibilityRuleSet({
    required this.id,
    required this.opportunityId,
    required this.version,
    required this.rules,
    required this.createdAt,
    required this.createdBy,
    required this.isActive,
  });

  final String id;
  final String opportunityId;
  final int version;
  final List<EligibilityRule> rules;
  final DateTime createdAt;
  final String createdBy;
  final bool isActive;

  EligibilityRuleSet copyWith({bool? isActive}) => EligibilityRuleSet(
    id: id,
    opportunityId: opportunityId,
    version: version,
    rules: rules,
    createdAt: createdAt,
    createdBy: createdBy,
    isActive: isActive ?? this.isActive,
  );
}

enum RuleEvaluationStatus {
  met,
  notMet,
  missingInformation,
  uncertain,
  skipped,
}

class EligibilityRuleResult {
  const EligibilityRuleResult({
    required this.rule,
    required this.status,
    required this.explanation,
    this.manuallyOverridden = false,
  });

  final EligibilityRule rule;
  final RuleEvaluationStatus status;
  final String explanation;
  final bool manuallyOverridden;
}

class DetailedEligibilityResult {
  const DetailedEligibilityResult({
    required this.percentage,
    required this.results,
    required this.recommendedActions,
    required this.officialSourceWarning,
    required this.calculatedAt,
    required this.ruleVersion,
  });

  final int percentage;
  final List<EligibilityRuleResult> results;
  final List<String> recommendedActions;
  final String officialSourceWarning;
  final DateTime calculatedAt;
  final int ruleVersion;

  List<EligibilityRuleResult> get mandatoryMet => results
      .where(
        (r) =>
            r.rule.type == EligibilityRuleType.mandatory &&
            r.status == RuleEvaluationStatus.met,
      )
      .toList();
  List<EligibilityRuleResult> get mandatoryNotMet => results
      .where(
        (r) =>
            r.rule.type == EligibilityRuleType.mandatory &&
            r.status == RuleEvaluationStatus.notMet,
      )
      .toList();
  List<EligibilityRuleResult> get missingInformation => results
      .where((r) => r.status == RuleEvaluationStatus.missingInformation)
      .toList();
  List<EligibilityRuleResult> get uncertainRequirements =>
      results.where((r) => r.status == RuleEvaluationStatus.uncertain).toList();

  String get disclaimer =>
      'Likely eligible based on your current profile. Confirm all '
      'requirements on the official application website.';
}

class EligibilityOverride {
  const EligibilityOverride({
    required this.ruleId,
    required this.status,
    required this.reason,
    required this.officerId,
    required this.createdAt,
  });
  final String ruleId;
  final RuleEvaluationStatus status;
  final String reason;
  final String officerId;
  final DateTime createdAt;
}
