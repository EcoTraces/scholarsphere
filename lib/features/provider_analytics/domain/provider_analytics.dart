class EngagementEvent {
  const EngagementEvent({
    required this.providerId,
    required this.opportunityId,
    required this.kind,
    required this.country,
    required this.studyLevel,
    required this.field,
    required this.occurredAt,
    this.userId,
    this.identifiableSharingConsent = false,
  });
  final String providerId;
  final String opportunityId;
  final String kind;
  final String country;
  final String studyLevel;
  final String field;
  final DateTime occurredAt;
  final String? userId;
  final bool identifiableSharingConsent;
}

class ProviderAnalyticsSnapshot {
  const ProviderAnalyticsSnapshot({
    required this.views,
    required this.saves,
    required this.applicationClicks,
    required this.countries,
    required this.studyLevels,
    required this.fields,
    required this.suppressed,
  });
  final int views;
  final int saves;
  final int applicationClicks;
  final Map<String, int> countries;
  final Map<String, int> studyLevels;
  final Map<String, int> fields;
  final bool suppressed;
}

abstract interface class ProviderAnalyticsRepository {
  Future<void> record(EngagementEvent event);
  Future<ProviderAnalyticsSnapshot> snapshot(String providerId);
  Future<String> exportCsv(String providerId);
}
