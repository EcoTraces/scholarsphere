import '../../opportunities/domain/opportunity.dart';
import '../domain/notification.dart';
import '../domain/notification_repository.dart';

class DemoNotificationRepository implements NotificationRepository {
  DemoNotificationRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final Map<String, NotificationPreferences> _preferences = {};
  final Map<String, List<ScholarSphereNotification>> _notifications = {};
  final Map<String, NotificationTemplate> _templates = {};

  @override
  Future<NotificationPreferences> getPreferences(String userId) async =>
      _preferences[userId] ?? const NotificationPreferences();

  @override
  Future<void> savePreferences(
    String userId,
    NotificationPreferences preferences,
  ) async {
    _preferences[userId] = preferences;
  }

  @override
  Future<List<ScholarSphereNotification>> getForUser(String userId) async {
    final records = _notifications.putIfAbsent(
      userId,
      () => [
        ScholarSphereNotification(
          id: 'welcome-$userId',
          userId: userId,
          type: NotificationEventType.matchingOpportunity,
          title: 'Welcome to ScholarSphere',
          message: 'Complete your profile to improve opportunity matches.',
          channels: const {NotificationChannel.inApp},
          scheduledFor: _clock(),
          createdAt: _clock(),
        ),
      ],
    );
    return [...records]
      ..sort((left, right) => left.scheduledFor.compareTo(right.scheduledFor));
  }

  @override
  Future<void> scheduleDeadlineReminders({
    required String userId,
    required Iterable<Opportunity> opportunities,
  }) async {
    final preferences = await getPreferences(userId);
    if (preferences.frequency == NotificationFrequency.disabled ||
        preferences.unsubscribedTypes.contains(
          NotificationEventType.deadlineReminder,
        )) {
      return;
    }
    final records = _notifications.putIfAbsent(userId, () => []);
    final now = _clock();
    for (final opportunity in opportunities.where(
      (item) => item.deadline.isAfter(now),
    )) {
      for (final days in preferences.reminderDays) {
        final id = '${opportunity.id}-deadline-$days';
        if (records.any((item) => item.id == id)) continue;
        records.add(
          ScholarSphereNotification(
            id: id,
            userId: userId,
            type: NotificationEventType.deadlineReminder,
            title: '$days-day deadline reminder',
            message:
                '${opportunity.title} closes in $days ${days == 1 ? 'day' : 'days'}.',
            channels: preferences.channels,
            scheduledFor: _outsideQuietHours(
              opportunity.deadline.subtract(Duration(days: days)),
              preferences,
            ),
            createdAt: now,
            opportunityId: opportunity.id,
            relatedEntityType: 'opportunity',
            relatedEntityId: opportunity.id,
            timezone: preferences.timezone,
            groupKey: preferences.groupNotifications
                ? 'deadline-${opportunity.id}'
                : null,
          ),
        );
      }
    }
  }

  @override
  Future<void> recordOpportunityEvent({
    required String userId,
    required Opportunity opportunity,
    required NotificationEventType type,
    required String message,
  }) async {
    final preferences = await getPreferences(userId);
    if (preferences.frequency == NotificationFrequency.disabled ||
        preferences.unsubscribedTypes.contains(type) ||
        !_eventEnabled(preferences, type)) {
      return;
    }
    final records = _notifications.putIfAbsent(userId, () => []);
    final today = _clock();
    final sentToday = records.where(
      (item) =>
          item.createdAt.year == today.year &&
          item.createdAt.month == today.month &&
          item.createdAt.day == today.day,
    );
    if (sentToday.length >= preferences.dailyLimit &&
        type != NotificationEventType.emergencySystemMessage) {
      return;
    }
    final id =
        '${opportunity.id}-${type.name}-${_clock().microsecondsSinceEpoch}';
    records.add(
      ScholarSphereNotification(
        id: id,
        userId: userId,
        type: type,
        title: _eventTitle(type),
        message: message,
        channels: preferences.channels,
        scheduledFor: _outsideQuietHours(_clock(), preferences),
        createdAt: _clock(),
        opportunityId: opportunity.id,
        relatedEntityType: 'opportunity',
        relatedEntityId: opportunity.id,
        timezone: preferences.timezone,
        groupKey: preferences.groupNotifications
            ? '${type.name}-${opportunity.id}'
            : null,
      ),
    );
  }

  @override
  Future<void> markRead(String userId, String notificationId) async {
    final records = _notifications[userId];
    if (records == null) return;
    final index = records.indexWhere((item) => item.id == notificationId);
    if (index != -1) records[index] = records[index].markRead(_clock());
  }

  bool _eventEnabled(
    NotificationPreferences preferences,
    NotificationEventType type,
  ) => switch (type) {
    NotificationEventType.matchingOpportunity =>
      preferences.matchingOpportunities,
    NotificationEventType.deadlineReminder => true,
    NotificationEventType.requirementsChanged ||
    NotificationEventType.deadlineChanged => preferences.opportunityChanges,
    NotificationEventType.opportunityVerified =>
      preferences.verificationUpdates,
    NotificationEventType.savedOpportunityExpired =>
      preferences.savedOpportunityExpiry,
    NotificationEventType.applicationProgress ||
    NotificationEventType.providerAnnouncement ||
    NotificationEventType.emergencySystemMessage => true,
  };

  String _eventTitle(NotificationEventType type) => switch (type) {
    NotificationEventType.matchingOpportunity => 'New matching opportunity',
    NotificationEventType.deadlineReminder => 'Deadline reminder',
    NotificationEventType.requirementsChanged => 'Requirements changed',
    NotificationEventType.deadlineChanged => 'Deadline changed',
    NotificationEventType.opportunityVerified => 'Opportunity verified',
    NotificationEventType.savedOpportunityExpired =>
      'Saved opportunity expired',
    NotificationEventType.applicationProgress => 'Application status updated',
    NotificationEventType.providerAnnouncement => 'Provider announcement',
    NotificationEventType.emergencySystemMessage => 'Important system message',
  };

  @override
  Future<List<ScholarSphereNotification>> getAllForAdministration() async =>
      _notifications.values.expand((records) => records).toList();

  @override
  Future<void> saveTemplate(NotificationTemplate template) async {
    _templates[template.id] = template;
  }

  @override
  Future<void> processDueNotifications() async {
    final now = _clock();
    for (final records in _notifications.values) {
      for (var index = 0; index < records.length; index++) {
        final record = records[index];
        if (record.status != NotificationDeliveryStatus.scheduled &&
            record.status != NotificationDeliveryStatus.queued &&
            record.status != NotificationDeliveryStatus.retrying) {
          continue;
        }
        if (record.scheduledFor.isAfter(now)) continue;
        records[index] = record.copyWith(
          status: NotificationDeliveryStatus.processing,
        );
        final hasConfiguredChannel = record.channels.any(
          {
            NotificationChannel.inApp,
            NotificationChannel.email,
            NotificationChannel.push,
          }.contains,
        );
        records[index] = record.copyWith(
          status: hasConfiguredChannel
              ? NotificationDeliveryStatus.delivered
              : NotificationDeliveryStatus.failed,
          sentAt: hasConfiguredChannel ? now : null,
          deliveredAt: hasConfiguredChannel ? now : null,
          failureReason: hasConfiguredChannel
              ? null
              : 'Delivery provider is not configured.',
        );
      }
    }
  }

  @override
  Future<void> retryFailed({int maximumRetries = 3}) async {
    for (final records in _notifications.values) {
      for (var index = 0; index < records.length; index++) {
        final record = records[index];
        if (record.status != NotificationDeliveryStatus.failed) continue;
        records[index] = record.retryCount >= maximumRetries
            ? record.copyWith(status: NotificationDeliveryStatus.expired)
            : record.copyWith(
                status: NotificationDeliveryStatus.retrying,
                retryCount: record.retryCount + 1,
              );
      }
    }
  }

  @override
  Future<void> cancel(String userId, String notificationId) async {
    final records = _notifications[userId];
    if (records == null) return;
    final index = records.indexWhere((item) => item.id == notificationId);
    if (index >= 0) {
      records[index] = records[index].copyWith(
        status: NotificationDeliveryStatus.cancelled,
      );
    }
  }

  @override
  Future<NotificationDeliveryAnalytics> getDeliveryAnalytics() async {
    final records = _notifications.values.expand((items) => items).toList();
    return NotificationDeliveryAnalytics(
      total: records.length,
      delivered: records
          .where((item) => item.status == NotificationDeliveryStatus.delivered)
          .length,
      read: records
          .where((item) => item.status == NotificationDeliveryStatus.read)
          .length,
      failed: records
          .where((item) => item.status == NotificationDeliveryStatus.failed)
          .length,
      retried: records.where((item) => item.retryCount > 0).length,
    );
  }

  DateTime _outsideQuietHours(
    DateTime scheduled,
    NotificationPreferences preferences,
  ) {
    final start = preferences.quietHoursStart;
    final end = preferences.quietHoursEnd;
    if (start == null || end == null) return scheduled;
    final inQuietHours = start > end
        ? scheduled.hour >= start || scheduled.hour < end
        : scheduled.hour >= start && scheduled.hour < end;
    if (!inQuietHours) return scheduled;
    final next = DateTime(scheduled.year, scheduled.month, scheduled.day, end);
    return next.isAfter(scheduled) ? next : next.add(const Duration(days: 1));
  }
}
