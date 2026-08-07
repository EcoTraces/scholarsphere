abstract interface class AnalyticsRepository {
  Future<void> recordOpportunityView({
    required String userId,
    required String opportunityId,
  });

  Future<Map<String, int>> getOpportunityViewCounts();
}
