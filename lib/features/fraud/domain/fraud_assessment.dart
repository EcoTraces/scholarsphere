enum FraudSignalType {
  personalAccountPayment,
  unofficialDomain,
  guaranteedSelection,
  credentialRequest,
  inconsistentDeadline,
  institutionImpersonation,
  shortenedLink,
  unrealisticBenefits,
  missingSponsor,
  alteredLinkDuplicate,
}

enum RiskSeverity { low, medium, high, critical }

enum OverallRiskLevel { low, moderate, high, critical }

class FraudSignal {
  const FraudSignal({
    required this.type,
    required this.severity,
    required this.userMessage,
    required this.reviewGuidance,
  });

  final FraudSignalType type;
  final RiskSeverity severity;
  final String userMessage;
  final String reviewGuidance;
}

class FraudAssessment {
  const FraudAssessment({
    required this.opportunityId,
    required this.assessedAt,
    required this.score,
    required this.level,
    required this.signals,
  });

  final String opportunityId;
  final DateTime assessedAt;
  final int score;
  final OverallRiskLevel level;
  final List<FraudSignal> signals;

  bool get hasWarnings => signals.isNotEmpty;

  String get levelLabel => switch (level) {
    OverallRiskLevel.low => 'Low automated risk',
    OverallRiskLevel.moderate => 'Review recommended',
    OverallRiskLevel.high => 'High-risk indicators',
    OverallRiskLevel.critical => 'Critical safety warning',
  };
}
