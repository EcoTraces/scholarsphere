import '../../profiles/domain/applicant_profile.dart';
import 'eligibility_rule.dart';

class EligibilityRuleEvaluator {
  const EligibilityRuleEvaluator({DateTime Function()? clock}) : _clock = clock;

  final DateTime Function()? _clock;

  DetailedEligibilityResult evaluate({
    required ApplicantProfile profile,
    required EligibilityRuleSet ruleSet,
    List<EligibilityOverride> overrides = const [],
  }) {
    final evaluated = <EligibilityRuleResult>[];
    final byRule = <String, RuleEvaluationStatus>{};
    final overrideByRule = {for (final value in overrides) value.ruleId: value};

    for (final rule in ruleSet.rules) {
      if (rule.type == EligibilityRuleType.conditional &&
          rule.conditionRuleId != null &&
          byRule[rule.conditionRuleId] != RuleEvaluationStatus.met) {
        evaluated.add(
          EligibilityRuleResult(
            rule: rule,
            status: RuleEvaluationStatus.skipped,
            explanation: 'This conditional rule does not currently apply.',
          ),
        );
        byRule[rule.id] = RuleEvaluationStatus.skipped;
        continue;
      }
      final manual = overrideByRule[rule.id];
      final result = manual == null
          ? _evaluateRule(profile, rule)
          : EligibilityRuleResult(
              rule: rule,
              status: manual.status,
              explanation: 'Manual override: ${manual.reason}',
              manuallyOverridden: true,
            );
      evaluated.add(result);
      byRule[rule.id] = result.status;
    }

    var earned = 0;
    var available = 0;
    var disqualified = false;
    for (final result in evaluated) {
      if ({
        EligibilityRuleType.informational,
        EligibilityRuleType.unknownOrUnverified,
      }.contains(result.rule.type)) {
        continue;
      }
      available += result.rule.weight;
      if (result.status == RuleEvaluationStatus.met) {
        earned += result.rule.weight;
        if (result.rule.type == EligibilityRuleType.disqualifying) {
          disqualified = true;
        }
      } else if (result.status == RuleEvaluationStatus.uncertain) {
        earned += (result.rule.weight / 2).round();
      }
    }
    final percentage = disqualified || available == 0
        ? 0
        : ((earned / available) * 100).round();
    final actions = <String>[
      for (final result in evaluated)
        if (result.status == RuleEvaluationStatus.missingInformation)
          'Update your profile: ${result.rule.label}.',
      for (final result in evaluated)
        if (result.status == RuleEvaluationStatus.notMet &&
            result.rule.type == EligibilityRuleType.mandatory)
          'Review the official requirement: ${result.rule.label}.',
      if (evaluated.any(
        (result) => result.rule.type == EligibilityRuleType.unknownOrUnverified,
      ))
        'Confirm unverified requirements on the official website.',
    ];
    return DetailedEligibilityResult(
      percentage: percentage.clamp(0, 100).toInt(),
      results: List.unmodifiable(evaluated),
      recommendedActions: List.unmodifiable(actions),
      officialSourceWarning: ruleSet.rules.every((rule) => rule.officialSource)
          ? 'Rules were recorded from the official source.'
          : 'Some rules are not confirmed by an official source.',
      calculatedAt: (_clock ?? DateTime.now)(),
      ruleVersion: ruleSet.version,
    );
  }

  EligibilityRuleResult _evaluateRule(
    ApplicantProfile profile,
    EligibilityRule rule,
  ) {
    final raw = _profileValue(profile, rule.attribute);
    if (raw == null || (raw is String && raw.trim().isEmpty)) {
      return EligibilityRuleResult(
        rule: rule,
        status: rule.type == EligibilityRuleType.unknownOrUnverified
            ? RuleEvaluationStatus.uncertain
            : RuleEvaluationStatus.missingInformation,
        explanation: 'Your profile does not contain enough information.',
      );
    }
    final met = _compare(raw, rule.operator, rule.values);
    return EligibilityRuleResult(
      rule: rule,
      status: met ? RuleEvaluationStatus.met : RuleEvaluationStatus.notMet,
      explanation: met
          ? 'Your current profile meets this rule.'
          : 'Your current profile does not meet this rule.',
    );
  }

  Object? _profileValue(ApplicantProfile profile, EligibilityAttribute value) =>
      switch (value) {
        EligibilityAttribute.nationality => profile.nationality,
        EligibilityAttribute.countryOfResidence => profile.countryOfResidence,
        EligibilityAttribute.academicLevel => profile.highestQualification,
        EligibilityAttribute.gpaOrClassification =>
          profile.academicClassification,
        EligibilityAttribute.age => _age(profile.dateOfBirth),
        EligibilityAttribute.languageTest => profile.englishTestStatus.name,
        EligibilityAttribute.workExperienceYears => profile.workExperienceYears,
        EligibilityAttribute.graduationYear => profile.graduationYear,
        EligibilityAttribute.fieldOfStudy => profile.degreeField,
        EligibilityAttribute.gender => profile.gender,
        EligibilityAttribute.disabilityCategory =>
          profile.specialEligibilityCategories,
        EligibilityAttribute.employmentStatus => profile.employmentStatus.name,
      };

  int? _age(DateTime? birthDate) {
    if (birthDate == null) return null;
    final now = (_clock ?? DateTime.now)();
    var age = now.year - birthDate.year;
    if (now.month < birthDate.month ||
        (now.month == birthDate.month && now.day < birthDate.day)) {
      age--;
    }
    return age;
  }

  bool _compare(Object raw, EligibilityOperator operator, List<String> values) {
    final normalized = raw is Iterable
        ? raw.map((value) => value.toString().toLowerCase()).toList()
        : [raw.toString().toLowerCase()];
    final targets = values.map((value) => value.toLowerCase()).toList();
    final number = double.tryParse(normalized.first);
    final targetNumbers = values.map(double.tryParse).toList();
    return switch (operator) {
      EligibilityOperator.equals ||
      EligibilityOperator.oneOf => normalized.any(targets.contains),
      EligibilityOperator.contains => normalized.any(
        (value) => targets.any(
          (target) => value.contains(target) || target.contains(value),
        ),
      ),
      EligibilityOperator.minimum =>
        number != null &&
            targetNumbers.firstOrNull != null &&
            number >= targetNumbers.first!,
      EligibilityOperator.maximum =>
        number != null &&
            targetNumbers.firstOrNull != null &&
            number <= targetNumbers.first!,
      EligibilityOperator.between =>
        number != null &&
            targetNumbers.length >= 2 &&
            targetNumbers[0] != null &&
            targetNumbers[1] != null &&
            number >= targetNumbers[0]! &&
            number <= targetNumbers[1]!,
      EligibilityOperator.present => normalized.any(
        (value) => value.isNotEmpty,
      ),
    };
  }
}
