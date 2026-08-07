import '../domain/analytics_repository.dart';

class DemoAnalyticsRepository implements AnalyticsRepository {
  final Map<String, int> _opportunityViews = {};

  @override
  Future<void> recordOpportunityView({
    required String userId,
    required String opportunityId,
  }) async {
    _opportunityViews.update(
      opportunityId,
      (count) => count + 1,
      ifAbsent: () => 1,
    );
  }

  @override
  Future<Map<String, int>> getOpportunityViewCounts() async => {
    ..._opportunityViews,
  };
}
