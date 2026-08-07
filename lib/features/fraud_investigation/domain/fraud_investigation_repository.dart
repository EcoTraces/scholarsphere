import 'fraud_case.dart';

abstract class FraudInvestigationRepository {
  Future<FraudCase> createCase(FraudCase fraudCase);
  Future<FraudCase> assign(String caseId, String investigatorId);
  Future<FraudCase> addEvidence(String caseId, FraudEvidence evidence);
  Future<FraudCase> addNote(String caseId, String investigatorId, String note);
  Future<FraudCase> restrict(String caseId, String investigatorId);
  Future<FraudCase> appeal(String caseId, String subjectId, String reason);
  Future<void> addWatchlistEntry(WatchlistEntry entry);
  Future<bool> isBlocked(FraudSubjectType type, String value);
  Future<List<FraudCase>> queue();
  Future<FraudAnalytics> analytics();
}

class FraudInvestigationFailure implements Exception {
  const FraudInvestigationFailure(this.message);
  final String message;
}
