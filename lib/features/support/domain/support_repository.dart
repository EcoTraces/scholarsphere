import 'support_models.dart';

abstract class SupportRepository {
  Future<SupportTicket> submitTicket({
    required String requesterId,
    required String subject,
    required SupportTicketCategory category,
    required SupportTicketPriority priority,
    required String message,
    List<SupportAttachment> attachments = const [],
  });
  Future<List<SupportTicket>> getForUser(String userId);
  Future<List<SupportTicket>> getAgentQueue();
  Future<SupportTicket?> getById(String ticketId);
  Future<SupportTicket> assign(String ticketId, String agentId);
  Future<SupportTicket> addMessage({
    required String ticketId,
    required String senderId,
    required String message,
    required bool isAgent,
    List<SupportAttachment> attachments = const [],
  });
  Future<SupportTicket> addInternalNote(
    String ticketId,
    String agentId,
    String note,
  );
  Future<SupportTicket> updateStatus(
    String ticketId,
    String actorId,
    SupportTicketStatus status, {
    String notes = '',
  });
  Future<SupportTicket> escalate(
    String ticketId,
    String actorId,
    String reason,
  );
  Future<List<KnowledgeArticle>> searchKnowledge(
    String query, {
    SupportTicketCategory? category,
  });
  Future<void> saveArticle(KnowledgeArticle article);
  Future<List<SupportResponseTemplate>> templates(
    SupportTicketCategory category,
  );
  Future<void> saveTemplate(SupportResponseTemplate template);
  Future<void> submitSurvey(SatisfactionSurvey survey);
  Future<SupportPerformanceReport> performanceReport();
}

class SupportFailure implements Exception {
  const SupportFailure(this.message);
  final String message;
}
