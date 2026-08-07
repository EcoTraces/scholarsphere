enum NotificationChannel { inApp, email, push, sms, whatsapp }

enum NotificationFrequency { immediate, dailyDigest, weeklyDigest, disabled }

enum NotificationEventType {
  matchingOpportunity,
  deadlineReminder,
  requirementsChanged,
  deadlineChanged,
  opportunityVerified,
  savedOpportunityExpired,
  applicationProgress,
  providerAnnouncement,
  emergencySystemMessage,
}

enum NotificationDeliveryStatus {
  scheduled,
  queued,
  processing,
  sent,
  delivered,
  read,
  failed,
  retrying,
  cancelled,
  expired,
}

class NotificationPreferences {
  const NotificationPreferences({
    this.channels = const {
      NotificationChannel.inApp,
      NotificationChannel.email,
      NotificationChannel.push,
    },
    this.frequency = NotificationFrequency.immediate,
    this.reminderDays = const {30, 14, 7, 3, 1},
    this.matchingOpportunities = true,
    this.opportunityChanges = true,
    this.verificationUpdates = true,
    this.savedOpportunityExpiry = true,
    this.quietHoursStart,
    this.quietHoursEnd,
    this.timezone = 'UTC',
    this.dailyLimit = 10,
    this.groupNotifications = true,
    this.unsubscribedTypes = const {},
  });

  final Set<NotificationChannel> channels;
  final NotificationFrequency frequency;
  final Set<int> reminderDays;
  final bool matchingOpportunities;
  final bool opportunityChanges;
  final bool verificationUpdates;
  final bool savedOpportunityExpiry;
  final int? quietHoursStart;
  final int? quietHoursEnd;
  final String timezone;
  final int dailyLimit;
  final bool groupNotifications;
  final Set<NotificationEventType> unsubscribedTypes;

  NotificationPreferences copyWith({
    Set<NotificationChannel>? channels,
    NotificationFrequency? frequency,
    Set<int>? reminderDays,
    bool? matchingOpportunities,
    bool? opportunityChanges,
    bool? verificationUpdates,
    bool? savedOpportunityExpiry,
    int? quietHoursStart,
    int? quietHoursEnd,
    String? timezone,
    int? dailyLimit,
    bool? groupNotifications,
    Set<NotificationEventType>? unsubscribedTypes,
  }) => NotificationPreferences(
    channels: channels ?? this.channels,
    frequency: frequency ?? this.frequency,
    reminderDays: reminderDays ?? this.reminderDays,
    matchingOpportunities: matchingOpportunities ?? this.matchingOpportunities,
    opportunityChanges: opportunityChanges ?? this.opportunityChanges,
    verificationUpdates: verificationUpdates ?? this.verificationUpdates,
    savedOpportunityExpiry:
        savedOpportunityExpiry ?? this.savedOpportunityExpiry,
    quietHoursStart: quietHoursStart ?? this.quietHoursStart,
    quietHoursEnd: quietHoursEnd ?? this.quietHoursEnd,
    timezone: timezone ?? this.timezone,
    dailyLimit: dailyLimit ?? this.dailyLimit,
    groupNotifications: groupNotifications ?? this.groupNotifications,
    unsubscribedTypes: unsubscribedTypes ?? this.unsubscribedTypes,
  );
}

class NotificationTemplate {
  const NotificationTemplate({
    required this.id,
    required this.type,
    required this.titleTemplate,
    required this.bodyTemplate,
    required this.channels,
  });
  final String id;
  final NotificationEventType type;
  final String titleTemplate;
  final String bodyTemplate;
  final Set<NotificationChannel> channels;
}

class ScholarSphereNotification {
  const ScholarSphereNotification({
    required this.id,
    required this.userId,
    required this.type,
    required this.title,
    required this.message,
    required this.channels,
    required this.scheduledFor,
    required this.createdAt,
    this.opportunityId,
    this.readAt,
    this.templateId,
    this.relatedEntityType,
    this.relatedEntityId,
    this.sentAt,
    this.deliveredAt,
    this.status = NotificationDeliveryStatus.scheduled,
    this.retryCount = 0,
    this.failureReason,
    this.timezone = 'UTC',
    this.groupKey,
  });

  final String id;
  final String userId;
  final NotificationEventType type;
  final String title;
  final String message;
  final Set<NotificationChannel> channels;
  final DateTime scheduledFor;
  final DateTime createdAt;
  final String? opportunityId;
  final DateTime? readAt;
  final String? templateId;
  final String? relatedEntityType;
  final String? relatedEntityId;
  final DateTime? sentAt;
  final DateTime? deliveredAt;
  final NotificationDeliveryStatus status;
  final int retryCount;
  final String? failureReason;
  final String timezone;
  final String? groupKey;

  bool get isRead => readAt != null;

  ScholarSphereNotification markRead(DateTime at) => ScholarSphereNotification(
    id: id,
    userId: userId,
    type: type,
    title: title,
    message: message,
    channels: channels,
    scheduledFor: scheduledFor,
    createdAt: createdAt,
    opportunityId: opportunityId,
    readAt: at,
    templateId: templateId,
    relatedEntityType: relatedEntityType,
    relatedEntityId: relatedEntityId,
    sentAt: sentAt,
    deliveredAt: deliveredAt,
    status: NotificationDeliveryStatus.read,
    retryCount: retryCount,
    failureReason: failureReason,
    timezone: timezone,
    groupKey: groupKey,
  );

  ScholarSphereNotification copyWith({
    NotificationDeliveryStatus? status,
    DateTime? sentAt,
    DateTime? deliveredAt,
    int? retryCount,
    String? failureReason,
    DateTime? scheduledFor,
  }) => ScholarSphereNotification(
    id: id,
    userId: userId,
    type: type,
    title: title,
    message: message,
    channels: channels,
    scheduledFor: scheduledFor ?? this.scheduledFor,
    createdAt: createdAt,
    opportunityId: opportunityId,
    readAt: readAt,
    templateId: templateId,
    relatedEntityType: relatedEntityType,
    relatedEntityId: relatedEntityId,
    sentAt: sentAt ?? this.sentAt,
    deliveredAt: deliveredAt ?? this.deliveredAt,
    status: status ?? this.status,
    retryCount: retryCount ?? this.retryCount,
    failureReason: failureReason ?? this.failureReason,
    timezone: timezone,
    groupKey: groupKey,
  );
}

class NotificationDeliveryAnalytics {
  const NotificationDeliveryAnalytics({
    required this.total,
    required this.delivered,
    required this.read,
    required this.failed,
    required this.retried,
  });
  final int total;
  final int delivered;
  final int read;
  final int failed;
  final int retried;
}
