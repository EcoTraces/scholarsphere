import 'moderation_case.dart';

abstract class ModerationRepository {
  Future<ModerationCase> submit(ModerationCase report);
  Future<List<ModerationCase>> getQueue();
  Future<List<ModerationCase>> getForReporter(String reporterId);
  Future<ModerationCase> assign(String caseId, String moderatorId);
  Future<ModerationCase> transition({
    required String caseId,
    required String actorId,
    required ModerationStatus status,
    required String notes,
    bool hideContent = false,
  });
  Future<ModerationCase> appeal(
    String caseId,
    String appellantId,
    String reason,
  );
  Future<ModerationAnalytics> analytics();
  Future<ModerationWarning> issueWarning({
    required String caseId,
    required String moderatorId,
    required String reason,
  });
  Future<List<ModerationWarning>> warningsFor(
    ReportedEntityType entityType,
    String entityId,
  );
}

class ModerationFailure implements Exception {
  const ModerationFailure(this.message);
  final String message;
}
