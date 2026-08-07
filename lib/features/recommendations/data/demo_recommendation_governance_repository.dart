import '../domain/recommendation_governance.dart';
import '../domain/recommendation_governance_repository.dart';

class DemoRecommendationGovernanceRepository
    implements RecommendationGovernanceRepository {
  final Map<String, PersonalizationControls> _controls = {};
  final List<RecommendationHistoryEntry> _history = [];
  final List<RecommendationFeedback> _feedback = [];

  @override
  Future<PersonalizationControls> getControls(String userId) async =>
      _controls[userId] ?? const PersonalizationControls();

  @override
  Future<void> saveControls(
    String userId,
    PersonalizationControls controls,
  ) async {
    _controls[userId] = controls;
  }

  @override
  Future<void> recordHistory(RecommendationHistoryEntry entry) async {
    _history.add(entry);
  }

  @override
  Future<List<RecommendationHistoryEntry>> getHistory(String userId) async =>
      _history.where((entry) => entry.userId == userId).toList();

  @override
  Future<void> resetHistory(String userId) async {
    _history.removeWhere((entry) => entry.userId == userId);
  }

  @override
  Future<void> recordFeedback(RecommendationFeedback feedback) async {
    _feedback.add(feedback);
    if ({
      RecommendationFeedbackType.dismissed,
      RecommendationFeedbackType.notRelevant,
    }.contains(feedback.type)) {
      final current =
          _controls[feedback.userId] ?? const PersonalizationControls();
      _controls[feedback.userId] = current.copyWith(
        hiddenOpportunityIds: {
          ...current.hiddenOpportunityIds,
          feedback.opportunityId,
        },
      );
    }
  }

  @override
  Future<List<RecommendationFeedback>> getFeedback(String userId) async =>
      _feedback.where((entry) => entry.userId == userId).toList();

  @override
  Future<RecommendationQualityReport> qualityReport() async {
    final total = _history.length;
    final dismissed = _feedback.where(
      (entry) =>
          entry.type == RecommendationFeedbackType.dismissed ||
          entry.type == RecommendationFeedbackType.notRelevant,
    );
    final helpful = _feedback.where(
      (entry) => entry.type == RecommendationFeedbackType.helpful,
    );
    final sponsored = _history.where(
      (entry) =>
          entry.labels.contains(RecommendationLabel.sponsoredOpportunity),
    );
    return RecommendationQualityReport(
      generatedCount: total,
      dismissalRate: total == 0 ? 0 : dismissed.length / total,
      helpfulRate: _feedback.isEmpty ? 0 : helpful.length / _feedback.length,
      countryDiversity: _history
          .map((entry) => entry.hostCountry)
          .toSet()
          .length,
      sponsoredShare: total == 0 ? 0 : sponsored.length / total,
      inappropriateReports: _feedback
          .where(
            (entry) => entry.type == RecommendationFeedbackType.inappropriate,
          )
          .length,
    );
  }
}
