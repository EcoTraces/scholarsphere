enum ReportedEntityType { opportunity, provider, user }

enum ModerationReportType {
  scam,
  incorrectDeadline,
  brokenLink,
  duplicateListing,
  misleadingContent,
  inappropriateContent,
  outdatedContent,
  harmfulContent,
}

enum ModerationStatus {
  submitted,
  underReview,
  evidenceRequired,
  escalated,
  resolved,
  rejected,
  contentCorrected,
  contentRemoved,
  providerSuspended,
  closed,
}

class ModerationEvidence {
  const ModerationEvidence({required this.location, required this.description});
  final String location;
  final String description;
}

class ModerationHistoryEntry {
  const ModerationHistoryEntry({
    required this.status,
    required this.actorId,
    required this.notes,
    required this.createdAt,
  });
  final ModerationStatus status;
  final String actorId;
  final String notes;
  final DateTime createdAt;
}

class ModerationCase {
  const ModerationCase({
    required this.id,
    required this.reporterId,
    required this.entityType,
    required this.entityId,
    required this.reportType,
    required this.description,
    required this.evidence,
    required this.status,
    required this.createdAt,
    required this.history,
    this.assignedModeratorId,
    this.moderationNotes,
    this.temporarilyHidden = false,
    this.appealReason,
  });

  final String id;
  final String reporterId;
  final ReportedEntityType entityType;
  final String entityId;
  final ModerationReportType reportType;
  final String description;
  final List<ModerationEvidence> evidence;
  final ModerationStatus status;
  final String? assignedModeratorId;
  final String? moderationNotes;
  final bool temporarilyHidden;
  final String? appealReason;
  final DateTime createdAt;
  final List<ModerationHistoryEntry> history;

  ModerationCase copyWith({
    ModerationStatus? status,
    String? assignedModeratorId,
    String? moderationNotes,
    bool? temporarilyHidden,
    String? appealReason,
    List<ModerationHistoryEntry>? history,
  }) => ModerationCase(
    id: id,
    reporterId: reporterId,
    entityType: entityType,
    entityId: entityId,
    reportType: reportType,
    description: description,
    evidence: evidence,
    status: status ?? this.status,
    assignedModeratorId: assignedModeratorId ?? this.assignedModeratorId,
    moderationNotes: moderationNotes ?? this.moderationNotes,
    temporarilyHidden: temporarilyHidden ?? this.temporarilyHidden,
    appealReason: appealReason ?? this.appealReason,
    createdAt: createdAt,
    history: history ?? this.history,
  );
}

class ModerationAnalytics {
  const ModerationAnalytics({
    required this.totalReports,
    required this.openReports,
    required this.removedContent,
    required this.suspendedProviders,
    required this.repeatOffenders,
  });
  final int totalReports;
  final int openReports;
  final int removedContent;
  final int suspendedProviders;
  final Map<String, int> repeatOffenders;
}

class ModerationWarning {
  const ModerationWarning({
    required this.id,
    required this.entityType,
    required this.entityId,
    required this.reason,
    required this.issuedBy,
    required this.issuedAt,
    required this.caseId,
  });
  final String id;
  final ReportedEntityType entityType;
  final String entityId;
  final String reason;
  final String issuedBy;
  final DateTime issuedAt;
  final String caseId;
}
