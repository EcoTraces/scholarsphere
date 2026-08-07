enum FraudSubjectType { opportunity, provider, source, user, domain, payment }

enum InvestigationRiskLevel { low, medium, high, critical }

enum FraudCaseStatus {
  opened,
  assigned,
  investigating,
  additionalVerificationRequired,
  restricted,
  resolved,
  rejected,
  appealed,
  closed,
}

class RiskScore {
  const RiskScore({
    required this.overall,
    required this.level,
    required this.providerRisk,
    required this.sourceRisk,
    required this.userBehaviourRisk,
    required this.domainRisk,
    required this.linkRisk,
    required this.paymentRisk,
    required this.impersonationRisk,
    required this.reasons,
  });
  final int overall;
  final InvestigationRiskLevel level;
  final int providerRisk;
  final int sourceRisk;
  final int userBehaviourRisk;
  final int domainRisk;
  final int linkRisk;
  final int paymentRisk;
  final int impersonationRisk;
  final List<String> reasons;
}

class FraudEvidence {
  const FraudEvidence({
    required this.id,
    required this.type,
    required this.location,
    required this.summary,
    required this.collectedAt,
    required this.collectedBy,
  });
  final String id;
  final String type;
  final String location;
  final String summary;
  final DateTime collectedAt;
  final String collectedBy;
}

class FraudCase {
  const FraudCase({
    required this.id,
    required this.subjectType,
    required this.subjectId,
    required this.risk,
    required this.status,
    required this.evidence,
    required this.investigatorNotes,
    required this.createdAt,
    required this.history,
    this.assignedInvestigatorId,
    this.appealReason,
  });
  final String id;
  final FraudSubjectType subjectType;
  final String subjectId;
  final RiskScore risk;
  final FraudCaseStatus status;
  final String? assignedInvestigatorId;
  final List<FraudEvidence> evidence;
  final List<String> investigatorNotes;
  final DateTime createdAt;
  final List<String> history;
  final String? appealReason;

  FraudCase copyWith({
    FraudCaseStatus? status,
    String? assignedInvestigatorId,
    List<FraudEvidence>? evidence,
    List<String>? investigatorNotes,
    List<String>? history,
    String? appealReason,
  }) => FraudCase(
    id: id,
    subjectType: subjectType,
    subjectId: subjectId,
    risk: risk,
    status: status ?? this.status,
    assignedInvestigatorId:
        assignedInvestigatorId ?? this.assignedInvestigatorId,
    evidence: evidence ?? this.evidence,
    investigatorNotes: investigatorNotes ?? this.investigatorNotes,
    createdAt: createdAt,
    history: history ?? this.history,
    appealReason: appealReason ?? this.appealReason,
  );
}

class WatchlistEntry {
  const WatchlistEntry({
    required this.id,
    required this.subjectType,
    required this.value,
    required this.reason,
    required this.blocked,
    required this.createdAt,
    required this.createdBy,
  });
  final String id;
  final FraudSubjectType subjectType;
  final String value;
  final String reason;
  final bool blocked;
  final DateTime createdAt;
  final String createdBy;
}

class FraudAnalytics {
  const FraudAnalytics({
    required this.openCases,
    required this.criticalCases,
    required this.restrictedSubjects,
    required this.watchlistEntries,
    required this.bySubjectType,
  });
  final int openCases;
  final int criticalCases;
  final int restrictedSubjects;
  final int watchlistEntries;
  final Map<FraudSubjectType, int> bySubjectType;
}
