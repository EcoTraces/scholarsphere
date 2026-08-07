enum SupportTicketCategory {
  accountAccess,
  profileProblem,
  opportunityInformation,
  eligibilityResult,
  applicationTracking,
  documentUpload,
  notificationProblem,
  providerVerification,
  fraudReport,
  privacyRequest,
  technicalIssue,
  billingIssue,
  generalInquiry,
}

enum SupportTicketPriority { low, normal, high, urgent }

enum SupportTicketStatus {
  open,
  assigned,
  inProgress,
  waitingForUser,
  escalated,
  resolved,
  closed,
  reopened,
}

class SupportAttachment {
  const SupportAttachment({
    required this.id,
    required this.name,
    required this.storageLocation,
    required this.contentType,
    required this.sizeBytes,
  });
  final String id;
  final String name;
  final String storageLocation;
  final String contentType;
  final int sizeBytes;
}

class SupportMessage {
  const SupportMessage({
    required this.id,
    required this.senderId,
    required this.message,
    required this.createdAt,
    required this.attachments,
    required this.isAgent,
  });
  final String id;
  final String senderId;
  final String message;
  final DateTime createdAt;
  final List<SupportAttachment> attachments;
  final bool isAgent;
}

class InternalSupportNote {
  const InternalSupportNote({
    required this.id,
    required this.agentId,
    required this.note,
    required this.createdAt,
  });
  final String id;
  final String agentId;
  final String note;
  final DateTime createdAt;
}

class SupportTicketEvent {
  const SupportTicketEvent({
    required this.status,
    required this.actorId,
    required this.createdAt,
    required this.notes,
  });
  final SupportTicketStatus status;
  final String actorId;
  final DateTime createdAt;
  final String notes;
}

class SupportTicket {
  const SupportTicket({
    required this.id,
    required this.requesterId,
    required this.subject,
    required this.category,
    required this.priority,
    required this.status,
    required this.messages,
    required this.internalNotes,
    required this.history,
    required this.createdAt,
    required this.updatedAt,
    required this.firstResponseDueAt,
    required this.resolutionDueAt,
    this.assignedAgentId,
    this.escalationReason,
    this.resolvedAt,
    this.closedAt,
  });

  final String id;
  final String requesterId;
  final String subject;
  final SupportTicketCategory category;
  final SupportTicketPriority priority;
  final SupportTicketStatus status;
  final String? assignedAgentId;
  final List<SupportMessage> messages;
  final List<InternalSupportNote> internalNotes;
  final List<SupportTicketEvent> history;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime firstResponseDueAt;
  final DateTime resolutionDueAt;
  final String? escalationReason;
  final DateTime? resolvedAt;
  final DateTime? closedAt;

  bool get firstResponseBreached =>
      !messages.any((message) => message.isAgent) &&
      DateTime.now().isAfter(firstResponseDueAt);
  bool get resolutionBreached =>
      resolvedAt == null && DateTime.now().isAfter(resolutionDueAt);

  SupportTicket copyWith({
    SupportTicketStatus? status,
    String? assignedAgentId,
    List<SupportMessage>? messages,
    List<InternalSupportNote>? internalNotes,
    List<SupportTicketEvent>? history,
    DateTime? updatedAt,
    String? escalationReason,
    DateTime? resolvedAt,
    DateTime? closedAt,
  }) => SupportTicket(
    id: id,
    requesterId: requesterId,
    subject: subject,
    category: category,
    priority: priority,
    status: status ?? this.status,
    assignedAgentId: assignedAgentId ?? this.assignedAgentId,
    messages: messages ?? this.messages,
    internalNotes: internalNotes ?? this.internalNotes,
    history: history ?? this.history,
    createdAt: createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    firstResponseDueAt: firstResponseDueAt,
    resolutionDueAt: resolutionDueAt,
    escalationReason: escalationReason ?? this.escalationReason,
    resolvedAt: resolvedAt ?? this.resolvedAt,
    closedAt: closedAt ?? this.closedAt,
  );
}

enum KnowledgeContentType {
  frequentlyAskedQuestion,
  article,
  tutorial,
  applicationHelp,
}

class KnowledgeArticle {
  const KnowledgeArticle({
    required this.id,
    required this.title,
    required this.summary,
    required this.content,
    required this.type,
    required this.category,
    required this.languageCode,
    required this.published,
    required this.updatedAt,
    required this.keywords,
  });
  final String id;
  final String title;
  final String summary;
  final String content;
  final KnowledgeContentType type;
  final SupportTicketCategory category;
  final String languageCode;
  final bool published;
  final DateTime updatedAt;
  final List<String> keywords;
}

class SupportResponseTemplate {
  const SupportResponseTemplate({
    required this.id,
    required this.name,
    required this.category,
    required this.subject,
    required this.body,
  });
  final String id;
  final String name;
  final SupportTicketCategory category;
  final String subject;
  final String body;
}

class SatisfactionSurvey {
  const SatisfactionSurvey({
    required this.ticketId,
    required this.userId,
    required this.rating,
    required this.createdAt,
    this.comment,
  });
  final String ticketId;
  final String userId;
  final int rating;
  final DateTime createdAt;
  final String? comment;
}

class SupportPerformanceReport {
  const SupportPerformanceReport({
    required this.totalTickets,
    required this.openTickets,
    required this.slaBreaches,
    required this.averageFirstResponseMinutes,
    required this.averageResolutionMinutes,
    required this.satisfactionScore,
    required this.byCategory,
  });
  final int totalTickets;
  final int openTickets;
  final int slaBreaches;
  final double averageFirstResponseMinutes;
  final double averageResolutionMinutes;
  final double satisfactionScore;
  final Map<SupportTicketCategory, int> byCategory;
}
