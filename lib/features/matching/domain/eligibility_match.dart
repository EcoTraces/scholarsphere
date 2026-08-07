enum MatchConditionStatus { matched, missing, uncertain }

class MatchCondition {
  const MatchCondition({
    required this.label,
    required this.status,
    required this.explanation,
  });

  final String label;
  final MatchConditionStatus status;
  final String explanation;
}

class EligibilityMatch {
  const EligibilityMatch({required this.score, required this.conditions});

  final int score;
  final List<MatchCondition> conditions;

  String get strength => switch (score) {
    >= 85 => 'Strong match',
    >= 70 => 'Good match',
    >= 50 => 'Possible match',
    _ => 'Weak match',
  };

  List<MatchCondition> get matched => conditions
      .where((item) => item.status == MatchConditionStatus.matched)
      .toList();

  List<MatchCondition> get missing => conditions
      .where((item) => item.status == MatchConditionStatus.missing)
      .toList();

  List<MatchCondition> get uncertain => conditions
      .where((item) => item.status == MatchConditionStatus.uncertain)
      .toList();
}
