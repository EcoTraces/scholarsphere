import '../domain/support_models.dart';
import '../domain/support_repository.dart';

class DemoSupportRepository implements SupportRepository {
  DemoSupportRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now {
    for (final article in _seedArticles) {
      _articles[article.id] = article;
    }
  }

  final DateTime Function() _clock;
  final Map<String, SupportTicket> _tickets = {};
  final Map<String, KnowledgeArticle> _articles = {};
  final Map<String, SupportResponseTemplate> _templates = {};
  final List<SatisfactionSurvey> _surveys = [];

  @override
  Future<SupportTicket> submitTicket({
    required String requesterId,
    required String subject,
    required SupportTicketCategory category,
    required SupportTicketPriority priority,
    required String message,
    List<SupportAttachment> attachments = const [],
  }) async {
    if (subject.trim().isEmpty || message.trim().isEmpty) {
      throw const SupportFailure('A subject and message are required.');
    }
    _validateAttachments(attachments);
    final now = _clock();
    final sla = _sla(priority);
    final ticket = SupportTicket(
      id: 'ticket-${now.microsecondsSinceEpoch}-${_tickets.length}',
      requesterId: requesterId,
      subject: subject.trim(),
      category: category,
      priority: priority,
      status: SupportTicketStatus.open,
      messages: [
        SupportMessage(
          id: 'message-${now.microsecondsSinceEpoch}',
          senderId: requesterId,
          message: message.trim(),
          createdAt: now,
          attachments: attachments,
          isAgent: false,
        ),
      ],
      internalNotes: const [],
      history: [
        SupportTicketEvent(
          status: SupportTicketStatus.open,
          actorId: requesterId,
          createdAt: now,
          notes: 'Ticket submitted.',
        ),
      ],
      createdAt: now,
      updatedAt: now,
      firstResponseDueAt: now.add(sla.$1),
      resolutionDueAt: now.add(sla.$2),
    );
    _tickets[ticket.id] = ticket;
    return ticket;
  }

  @override
  Future<List<SupportTicket>> getForUser(String userId) async =>
      _tickets.values.where((ticket) => ticket.requesterId == userId).toList()
        ..sort((a, b) => b.updatedAt.compareTo(a.updatedAt));

  @override
  Future<List<SupportTicket>> getAgentQueue() async =>
      _tickets.values
          .where(
            (ticket) => !{
              SupportTicketStatus.closed,
              SupportTicketStatus.resolved,
            }.contains(ticket.status),
          )
          .toList()
        ..sort((a, b) {
          final priority = b.priority.index.compareTo(a.priority.index);
          return priority != 0 ? priority : a.createdAt.compareTo(b.createdAt);
        });

  @override
  Future<SupportTicket?> getById(String ticketId) async => _tickets[ticketId];

  @override
  Future<SupportTicket> assign(String ticketId, String agentId) => _transition(
    ticketId,
    agentId,
    SupportTicketStatus.assigned,
    'Assigned to support agent.',
    assignedAgentId: agentId,
  );

  @override
  Future<SupportTicket> addMessage({
    required String ticketId,
    required String senderId,
    required String message,
    required bool isAgent,
    List<SupportAttachment> attachments = const [],
  }) async {
    final ticket = _require(ticketId);
    if (ticket.status == SupportTicketStatus.closed) {
      throw const SupportFailure('Closed tickets must be reopened first.');
    }
    if (message.trim().isEmpty) {
      throw const SupportFailure('A message is required.');
    }
    _validateAttachments(attachments);
    final now = _clock();
    final updated = ticket.copyWith(
      status: isAgent
          ? SupportTicketStatus.waitingForUser
          : SupportTicketStatus.inProgress,
      messages: [
        ...ticket.messages,
        SupportMessage(
          id: 'message-${now.microsecondsSinceEpoch}',
          senderId: senderId,
          message: message.trim(),
          createdAt: now,
          attachments: attachments,
          isAgent: isAgent,
        ),
      ],
      updatedAt: now,
    );
    _tickets[ticketId] = updated;
    return updated;
  }

  @override
  Future<SupportTicket> addInternalNote(
    String ticketId,
    String agentId,
    String note,
  ) async {
    final ticket = _require(ticketId);
    if (note.trim().isEmpty) {
      throw const SupportFailure('An internal note is required.');
    }
    final now = _clock();
    final updated = ticket.copyWith(
      internalNotes: [
        ...ticket.internalNotes,
        InternalSupportNote(
          id: 'note-${now.microsecondsSinceEpoch}',
          agentId: agentId,
          note: note.trim(),
          createdAt: now,
        ),
      ],
      updatedAt: now,
    );
    _tickets[ticketId] = updated;
    return updated;
  }

  @override
  Future<SupportTicket> updateStatus(
    String ticketId,
    String actorId,
    SupportTicketStatus status, {
    String notes = '',
  }) {
    final current = _require(ticketId);
    if (status == SupportTicketStatus.reopened &&
        !{
          SupportTicketStatus.resolved,
          SupportTicketStatus.closed,
        }.contains(current.status)) {
      throw const SupportFailure('Only resolved or closed tickets can reopen.');
    }
    return _transition(ticketId, actorId, status, notes);
  }

  @override
  Future<SupportTicket> escalate(
    String ticketId,
    String actorId,
    String reason,
  ) => _transition(
    ticketId,
    actorId,
    SupportTicketStatus.escalated,
    reason,
    escalationReason: reason,
  );

  @override
  Future<List<KnowledgeArticle>> searchKnowledge(
    String query, {
    SupportTicketCategory? category,
  }) async {
    final normalized = query.trim().toLowerCase();
    return _articles.values.where((article) {
      if (!article.published ||
          (category != null && article.category != category)) {
        return false;
      }
      return normalized.isEmpty ||
          article.title.toLowerCase().contains(normalized) ||
          article.summary.toLowerCase().contains(normalized) ||
          article.keywords.any(
            (keyword) => keyword.toLowerCase().contains(normalized),
          );
    }).toList();
  }

  @override
  Future<void> saveArticle(KnowledgeArticle article) async {
    _articles[article.id] = article;
  }

  @override
  Future<List<SupportResponseTemplate>> templates(
    SupportTicketCategory category,
  ) async => _templates.values
      .where((template) => template.category == category)
      .toList();

  @override
  Future<void> saveTemplate(SupportResponseTemplate template) async {
    _templates[template.id] = template;
  }

  @override
  Future<void> submitSurvey(SatisfactionSurvey survey) async {
    if (survey.rating < 1 || survey.rating > 5) {
      throw const SupportFailure('Satisfaction rating must be from 1 to 5.');
    }
    final ticket = _require(survey.ticketId);
    if (ticket.requesterId != survey.userId ||
        !{
          SupportTicketStatus.resolved,
          SupportTicketStatus.closed,
        }.contains(ticket.status)) {
      throw const SupportFailure(
        'Surveys are available to the requester after resolution.',
      );
    }
    _surveys.removeWhere(
      (item) =>
          item.ticketId == survey.ticketId && item.userId == survey.userId,
    );
    _surveys.add(survey);
  }

  @override
  Future<SupportPerformanceReport> performanceReport() async {
    final tickets = _tickets.values.toList();
    final now = _clock();
    final firstResponses = <int>[];
    final resolutions = <int>[];
    final byCategory = <SupportTicketCategory, int>{};
    var breaches = 0;
    for (final ticket in tickets) {
      byCategory.update(
        ticket.category,
        (count) => count + 1,
        ifAbsent: () => 1,
      );
      final agentMessages = ticket.messages.where((message) => message.isAgent);
      if (agentMessages.isNotEmpty) {
        firstResponses.add(
          agentMessages.first.createdAt.difference(ticket.createdAt).inMinutes,
        );
      } else if (now.isAfter(ticket.firstResponseDueAt)) {
        breaches++;
      }
      if (ticket.resolvedAt != null) {
        resolutions.add(
          ticket.resolvedAt!.difference(ticket.createdAt).inMinutes,
        );
      } else if (now.isAfter(ticket.resolutionDueAt)) {
        breaches++;
      }
    }
    return SupportPerformanceReport(
      totalTickets: tickets.length,
      openTickets: tickets
          .where(
            (ticket) => !{
              SupportTicketStatus.resolved,
              SupportTicketStatus.closed,
            }.contains(ticket.status),
          )
          .length,
      slaBreaches: breaches,
      averageFirstResponseMinutes: _average(firstResponses),
      averageResolutionMinutes: _average(resolutions),
      satisfactionScore: _surveys.isEmpty
          ? 0
          : _average(_surveys.map((s) => s.rating)),
      byCategory: byCategory,
    );
  }

  Future<SupportTicket> _transition(
    String ticketId,
    String actorId,
    SupportTicketStatus status,
    String notes, {
    String? assignedAgentId,
    String? escalationReason,
  }) async {
    final ticket = _require(ticketId);
    final now = _clock();
    final updated = ticket.copyWith(
      status: status,
      assignedAgentId: assignedAgentId,
      escalationReason: escalationReason,
      resolvedAt: status == SupportTicketStatus.resolved ? now : null,
      closedAt: status == SupportTicketStatus.closed ? now : null,
      updatedAt: now,
      history: [
        ...ticket.history,
        SupportTicketEvent(
          status: status,
          actorId: actorId,
          createdAt: now,
          notes: notes,
        ),
      ],
    );
    _tickets[ticketId] = updated;
    return updated;
  }

  SupportTicket _require(String id) {
    final ticket = _tickets[id];
    if (ticket == null) throw const SupportFailure('Support ticket not found.');
    return ticket;
  }

  (Duration, Duration) _sla(SupportTicketPriority priority) =>
      switch (priority) {
        SupportTicketPriority.urgent => (
          const Duration(minutes: 30),
          const Duration(hours: 4),
        ),
        SupportTicketPriority.high => (
          const Duration(hours: 2),
          const Duration(hours: 12),
        ),
        SupportTicketPriority.normal => (
          const Duration(hours: 8),
          const Duration(days: 2),
        ),
        SupportTicketPriority.low => (
          const Duration(days: 1),
          const Duration(days: 5),
        ),
      };

  void _validateAttachments(List<SupportAttachment> attachments) {
    for (final attachment in attachments) {
      if (attachment.sizeBytes > 10 * 1024 * 1024) {
        throw const SupportFailure('Attachments cannot exceed 10 MB.');
      }
      if ({
        'application/x-msdownload',
        'application/x-executable',
      }.contains(attachment.contentType)) {
        throw const SupportFailure('Executable attachments are not allowed.');
      }
    }
  }

  double _average(Iterable<int> values) {
    final list = values.toList();
    return list.isEmpty
        ? 0
        : list.reduce((left, right) => left + right) / list.length;
  }
}

final _seedArticles = [
  KnowledgeArticle(
    id: 'kb-profile',
    title: 'Complete your applicant profile',
    summary: 'Add academic and eligibility details for better matching.',
    content:
        'Open your profile from the account menu and complete each relevant field.',
    type: KnowledgeContentType.tutorial,
    category: SupportTicketCategory.profileProblem,
    languageCode: 'en',
    published: true,
    updatedAt: DateTime(2026, 7, 29),
    keywords: const ['profile', 'matching', 'academic'],
  ),
  KnowledgeArticle(
    id: 'kb-eligibility',
    title: 'Understanding eligibility results',
    summary: 'Eligibility results are guidance, not acceptance guarantees.',
    content:
        'Review missing and uncertain requirements, then confirm the official source.',
    type: KnowledgeContentType.frequentlyAskedQuestion,
    category: SupportTicketCategory.eligibilityResult,
    languageCode: 'en',
    published: true,
    updatedAt: DateTime(2026, 7, 29),
    keywords: const ['eligibility', 'score', 'requirements'],
  ),
];
