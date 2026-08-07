import '../domain/provider_analytics.dart';

class DemoProviderAnalyticsRepository implements ProviderAnalyticsRepository {
  DemoProviderAnalyticsRepository({this.minimumCohortSize = 3});
  final int minimumCohortSize;
  final List<EngagementEvent> _events = [];

  @override
  Future<void> record(EngagementEvent event) async => _events.add(event);

  @override
  Future<ProviderAnalyticsSnapshot> snapshot(String providerId) async {
    final events = _events.where((event) => event.providerId == providerId);
    final distinctUsers = events
        .map((event) => event.userId)
        .whereType<String>()
        .toSet();
    final suppressed = distinctUsers.length < minimumCohortSize;
    Map<String, int> group(String Function(EngagementEvent) select) {
      if (suppressed) return {};
      final result = <String, int>{};
      for (final event in events) {
        result.update(select(event), (value) => value + 1, ifAbsent: () => 1);
      }
      return result;
    }

    int count(String kind) =>
        events.where((event) => event.kind == kind).length;
    return ProviderAnalyticsSnapshot(
      views: count('view'),
      saves: count('save'),
      applicationClicks: count('application_click'),
      countries: group((event) => event.country),
      studyLevels: group((event) => event.studyLevel),
      fields: group((event) => event.field),
      suppressed: suppressed,
    );
  }

  @override
  Future<String> exportCsv(String providerId) async {
    final data = await snapshot(providerId);
    return 'metric,value\nviews,${data.views}\nsaves,${data.saves}\n'
        'application_clicks,${data.applicationClicks}\n';
  }
}
