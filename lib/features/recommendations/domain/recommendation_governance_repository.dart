import 'recommendation_governance.dart';

abstract class RecommendationGovernanceRepository {
  Future<PersonalizationControls> getControls(String userId);
  Future<void> saveControls(String userId, PersonalizationControls controls);
  Future<void> recordHistory(RecommendationHistoryEntry entry);
  Future<List<RecommendationHistoryEntry>> getHistory(String userId);
  Future<void> resetHistory(String userId);
  Future<void> recordFeedback(RecommendationFeedback feedback);
  Future<List<RecommendationFeedback>> getFeedback(String userId);
  Future<RecommendationQualityReport> qualityReport();
}
