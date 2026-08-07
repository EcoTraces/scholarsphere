import '../../opportunities/domain/opportunity.dart';
import 'notification.dart';

abstract interface class NotificationRepository {
  Future<NotificationPreferences> getPreferences(String userId);

  Future<void> savePreferences(
    String userId,
    NotificationPreferences preferences,
  );

  Future<List<ScholarSphereNotification>> getForUser(String userId);

  Future<void> scheduleDeadlineReminders({
    required String userId,
    required Iterable<Opportunity> opportunities,
  });

  Future<void> recordOpportunityEvent({
    required String userId,
    required Opportunity opportunity,
    required NotificationEventType type,
    required String message,
  });

  Future<void> markRead(String userId, String notificationId);

  Future<List<ScholarSphereNotification>> getAllForAdministration();

  Future<void> saveTemplate(NotificationTemplate template);
  Future<void> processDueNotifications();
  Future<void> retryFailed({int maximumRetries = 3});
  Future<void> cancel(String userId, String notificationId);
  Future<NotificationDeliveryAnalytics> getDeliveryAnalytics();
}
