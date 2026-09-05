import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../opportunities/domain/opportunity.dart';
import '../../security/domain/security_backend_contracts.dart';
import '../domain/notification.dart';
import '../domain/notification_repository.dart';

/// Reads and writes real, per-user notification data from the ScholarSphere
/// Python backend (scholarsphere_backend/).
///
/// This is the live replacement for [DemoNotificationRepository]. In-app
/// delivery is the only real channel this backend ships - email/push/SMS
/// records are created but never actually dispatched (no delivery provider
/// is integrated anywhere in this app), matching the honest gap already
/// disclosed for the existing reverification-reminder Celery task.
///
/// [processDueNotifications] is a documented no-op here: [getForUser] (the
/// backend's `GET /notifications`) already flips the caller's own due
/// in-app notifications to delivered as a side effect of listing them, and
/// the system-wide "delivered even if the app is never opened" guarantee is
/// owned server-side by Celery beat, not by any client call. The method
/// stays only so [NotificationCenterScreen]'s existing `.then()` chain
/// keeps compiling unchanged.
class ApiNotificationRepository implements NotificationRepository {
  ApiNotificationRepository({
    String? baseUrl,
    http.Client? client,
    firebase.FirebaseAuth? auth,
  }) : baseUrl = baseUrl ?? _defaultBaseUrl,
       _client = client ?? http.Client(),
       _authOverride = auth {
    if (kReleaseMode) {
      TransportSecurityPolicy.requireHttps(Uri.parse(this.baseUrl));
    }
  }

  static const _defaultBaseUrl = String.fromEnvironment(
    'SCHOLARSPHERE_API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  final String baseUrl;
  final http.Client _client;
  final firebase.FirebaseAuth? _authOverride;

  firebase.FirebaseAuth get _auth =>
      _authOverride ?? firebase.FirebaseAuth.instance;

  @override
  Future<NotificationPreferences> getPreferences(String userId) async {
    final body = await _get('/notifications/preferences');
    return _toPreferences(body as Map<String, dynamic>);
  }

  @override
  Future<void> savePreferences(
    String userId,
    NotificationPreferences preferences,
  ) async {
    await _put('/notifications/preferences', _preferencesBody(preferences));
  }

  @override
  Future<List<ScholarSphereNotification>> getForUser(String userId) async {
    final body = await _get('/notifications');
    final items = body as List<dynamic>;
    return items
        .map((item) => _toNotification(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> scheduleDeadlineReminders({
    required String userId,
    required Iterable<Opportunity> opportunities,
  }) async {
    final ids = opportunities.map((item) => item.id).toList();
    if (ids.isEmpty) return;
    await _post('/notifications/deadline-reminders', {'opportunity_ids': ids});
  }

  @override
  Future<void> recordOpportunityEvent({
    required String userId,
    required Opportunity opportunity,
    required NotificationEventType type,
    required String message,
  }) async {
    await _post('/notifications/events', {
      'user_id': userId,
      'opportunity_id': opportunity.id,
      'type': _eventTypeToWire(type),
      'message': message,
    });
  }

  @override
  Future<void> markRead(String userId, String notificationId) async {
    await _post('/notifications/$notificationId/read', const {});
  }

  @override
  Future<List<ScholarSphereNotification>> getAllForAdministration() async {
    final records = <ScholarSphereNotification>[];
    var page = 1;
    const pageSize = 100;
    while (true) {
      final body =
          await _get('/notifications/admin', {
                'page': '$page',
                'page_size': '$pageSize',
              })
              as Map<String, dynamic>;
      final items = (body['items'] as List<dynamic>)
          .map((item) => _toNotification(item as Map<String, dynamic>))
          .toList();
      records.addAll(items);
      if (items.length < pageSize) break;
      page += 1;
    }
    return records;
  }

  @override
  Future<void> saveTemplate(NotificationTemplate template) async {
    await _put('/notifications/admin/templates/${template.id}', {
      'type': _eventTypeToWire(template.type),
      'title_template': template.titleTemplate,
      'body_template': template.bodyTemplate,
      'channels': template.channels.map(_channelToWire).toList(),
    });
  }

  @override
  Future<void> processDueNotifications() async {}

  @override
  Future<void> retryFailed({int maximumRetries = 3}) async {
    await _post('/notifications/admin/retry-failed', {
      'maximum_retries': maximumRetries,
    });
  }

  @override
  Future<void> cancel(String userId, String notificationId) async {
    await _post('/notifications/$notificationId/cancel', const {});
  }

  @override
  Future<NotificationDeliveryAnalytics> getDeliveryAnalytics() async {
    final body = await _get('/notifications/admin/analytics');
    final json = body as Map<String, dynamic>;
    return NotificationDeliveryAnalytics(
      total: json['total'] as int,
      delivered: json['delivered'] as int,
      read: json['read'] as int,
      failed: json['failed'] as int,
      retried: json['retried'] as int,
    );
  }

  Map<String, dynamic> _preferencesBody(NotificationPreferences preferences) =>
      {
        'channels': preferences.channels.map(_channelToWire).toList(),
        'frequency': _frequencyToWire(preferences.frequency),
        'reminder_days': preferences.reminderDays.toList(),
        'matching_opportunities': preferences.matchingOpportunities,
        'opportunity_changes': preferences.opportunityChanges,
        'verification_updates': preferences.verificationUpdates,
        'saved_opportunity_expiry': preferences.savedOpportunityExpiry,
        'quiet_hours_start': preferences.quietHoursStart,
        'quiet_hours_end': preferences.quietHoursEnd,
        'timezone': preferences.timezone,
        'daily_limit': preferences.dailyLimit,
        'group_notifications': preferences.groupNotifications,
        'unsubscribed_types': preferences.unsubscribedTypes
            .map(_eventTypeToWire)
            .toList(),
      };

  NotificationPreferences _toPreferences(Map<String, dynamic> json) =>
      NotificationPreferences(
        channels: (json['channels'] as List<dynamic>)
            .map((item) => _channelFromWire(item as String))
            .toSet(),
        frequency: _frequencyFromWire(json['frequency'] as String),
        reminderDays: (json['reminder_days'] as List<dynamic>)
            .map((item) => item as int)
            .toSet(),
        matchingOpportunities: json['matching_opportunities'] as bool,
        opportunityChanges: json['opportunity_changes'] as bool,
        verificationUpdates: json['verification_updates'] as bool,
        savedOpportunityExpiry: json['saved_opportunity_expiry'] as bool,
        quietHoursStart: json['quiet_hours_start'] as int?,
        quietHoursEnd: json['quiet_hours_end'] as int?,
        timezone: json['timezone'] as String,
        dailyLimit: json['daily_limit'] as int,
        groupNotifications: json['group_notifications'] as bool,
        unsubscribedTypes: (json['unsubscribed_types'] as List<dynamic>)
            .map((item) => _eventTypeFromWire(item as String))
            .toSet(),
      );

  ScholarSphereNotification _toNotification(Map<String, dynamic> json) =>
      ScholarSphereNotification(
        id: json['id'] as String,
        userId: json['user_id'] as String,
        type: _eventTypeFromWire(json['type'] as String),
        title: json['title'] as String,
        message: json['message'] as String,
        channels: (json['channels'] as List<dynamic>)
            .map((item) => _channelFromWire(item as String))
            .toSet(),
        scheduledFor: DateTime.parse(json['scheduled_for'] as String),
        createdAt: DateTime.parse(json['created_at'] as String),
        opportunityId: json['opportunity_id'] as String?,
        readAt: _dateTime(json['read_at']),
        templateId: json['template_id'] as String?,
        relatedEntityType: json['related_entity_type'] as String?,
        relatedEntityId: json['related_entity_id'] as String?,
        sentAt: _dateTime(json['sent_at']),
        deliveredAt: _dateTime(json['delivered_at']),
        status: _statusFromWire(json['status'] as String),
        retryCount: json['retry_count'] as int,
        failureReason: json['failure_reason'] as String?,
        timezone: json['timezone'] as String,
        groupKey: json['group_key'] as String?,
      );

  static DateTime? _dateTime(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  // Keep these four maps in sync with app/schemas/notification.py's wire maps.
  static String _channelToWire(NotificationChannel channel) =>
      switch (channel) {
        NotificationChannel.inApp => 'inApp',
        NotificationChannel.email => 'email',
        NotificationChannel.push => 'push',
        NotificationChannel.sms => 'sms',
        NotificationChannel.whatsapp => 'whatsapp',
      };

  static NotificationChannel _channelFromWire(String value) => switch (value) {
    'inApp' => NotificationChannel.inApp,
    'email' => NotificationChannel.email,
    'push' => NotificationChannel.push,
    'sms' => NotificationChannel.sms,
    'whatsapp' => NotificationChannel.whatsapp,
    _ => throw LiveBackendException('Unknown notification channel: $value'),
  };

  static String _frequencyToWire(NotificationFrequency frequency) =>
      switch (frequency) {
        NotificationFrequency.immediate => 'immediate',
        NotificationFrequency.dailyDigest => 'dailyDigest',
        NotificationFrequency.weeklyDigest => 'weeklyDigest',
        NotificationFrequency.disabled => 'disabled',
      };

  static NotificationFrequency _frequencyFromWire(String value) =>
      switch (value) {
        'immediate' => NotificationFrequency.immediate,
        'dailyDigest' => NotificationFrequency.dailyDigest,
        'weeklyDigest' => NotificationFrequency.weeklyDigest,
        'disabled' => NotificationFrequency.disabled,
        _ => throw LiveBackendException(
          'Unknown notification frequency: $value',
        ),
      };

  static String _eventTypeToWire(NotificationEventType type) => switch (type) {
    NotificationEventType.matchingOpportunity => 'matchingOpportunity',
    NotificationEventType.deadlineReminder => 'deadlineReminder',
    NotificationEventType.requirementsChanged => 'requirementsChanged',
    NotificationEventType.deadlineChanged => 'deadlineChanged',
    NotificationEventType.opportunityVerified => 'opportunityVerified',
    NotificationEventType.savedOpportunityExpired => 'savedOpportunityExpired',
    NotificationEventType.applicationProgress => 'applicationProgress',
    NotificationEventType.providerAnnouncement => 'providerAnnouncement',
    NotificationEventType.emergencySystemMessage => 'emergencySystemMessage',
  };

  static NotificationEventType _eventTypeFromWire(
    String value,
  ) => switch (value) {
    'matchingOpportunity' => NotificationEventType.matchingOpportunity,
    'deadlineReminder' => NotificationEventType.deadlineReminder,
    'requirementsChanged' => NotificationEventType.requirementsChanged,
    'deadlineChanged' => NotificationEventType.deadlineChanged,
    'opportunityVerified' => NotificationEventType.opportunityVerified,
    'savedOpportunityExpired' => NotificationEventType.savedOpportunityExpired,
    'applicationProgress' => NotificationEventType.applicationProgress,
    'providerAnnouncement' => NotificationEventType.providerAnnouncement,
    'emergencySystemMessage' => NotificationEventType.emergencySystemMessage,
    _ => throw LiveBackendException('Unknown notification event type: $value'),
  };

  static NotificationDeliveryStatus _statusFromWire(String value) =>
      switch (value) {
        'scheduled' => NotificationDeliveryStatus.scheduled,
        'queued' => NotificationDeliveryStatus.queued,
        'processing' => NotificationDeliveryStatus.processing,
        'sent' => NotificationDeliveryStatus.sent,
        'delivered' => NotificationDeliveryStatus.delivered,
        'read' => NotificationDeliveryStatus.read,
        'failed' => NotificationDeliveryStatus.failed,
        'retrying' => NotificationDeliveryStatus.retrying,
        'cancelled' => NotificationDeliveryStatus.cancelled,
        'expired' => NotificationDeliveryStatus.expired,
        _ => throw LiveBackendException('Unknown delivery status: $value'),
      };

  Future<dynamic> _get(
    String path, [
    Map<String, String> query = const {},
  ]) async {
    final headers = await _headers();
    final uri = Uri.parse(
      '$baseUrl$path',
    ).replace(queryParameters: query.isEmpty ? null : query);
    return _handle(() => _client.get(uri, headers: headers));
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.post(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _put(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.put(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _handle(Future<http.Response> Function() request) async {
    late final http.Response response;
    try {
      response = await request();
    } on Exception catch (error) {
      throw LiveBackendException(
        'Could not reach the ScholarSphere backend: $error',
      );
    }
    if (response.statusCode == 401) {
      throw const LiveBackendException(
        'Sign-in expired. Sign in again to view notifications.',
        statusCode: 401,
      );
    }
    if (response.statusCode >= 400) {
      throw LiveBackendException(
        'The ScholarSphere backend returned an error.',
        statusCode: response.statusCode,
      );
    }
    if (response.body.isEmpty) return null;
    return jsonDecode(response.body);
  }

  Future<Map<String, String>> _headers() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const LiveBackendException(
        'Sign in to view notifications.',
        statusCode: 401,
      );
    }
    final token = await user.getIdToken();
    return {
      'Authorization': 'Bearer $token',
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
  }

  void dispose() => _client.close();
}
