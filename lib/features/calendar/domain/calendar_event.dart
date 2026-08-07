enum CalendarEventType {
  opportunityDeadline,
  application,
  interview,
  documentSubmission,
  followUp,
}

enum DeadlineState {
  upcoming,
  closingSoon,
  today,
  passed,
  extended,
  changed,
  unconfirmed,
  rollingDeadline,
}

enum CalendarProvider { google, outlook, ics }

class RecurrenceRule {
  const RecurrenceRule({
    required this.frequency,
    required this.interval,
    this.count,
    this.until,
  });
  final String frequency;
  final int interval;
  final int? count;
  final DateTime? until;
}

class CalendarEvent {
  const CalendarEvent({
    required this.id,
    required this.userId,
    required this.title,
    required this.description,
    required this.type,
    required this.startsAt,
    required this.endsAt,
    required this.timezone,
    required this.reminderMinutes,
    required this.deadlineState,
    required this.relatedEntityId,
    required this.createdAt,
    this.previousStartsAt,
    this.recurrence,
    this.externalCalendarId,
  });
  final String id;
  final String userId;
  final String title;
  final String description;
  final CalendarEventType type;
  final DateTime startsAt;
  final DateTime endsAt;
  final String timezone;
  final Set<int> reminderMinutes;
  final DeadlineState deadlineState;
  final String? relatedEntityId;
  final DateTime? previousStartsAt;
  final RecurrenceRule? recurrence;
  final String? externalCalendarId;
  final DateTime createdAt;

  CalendarEvent copyWith({
    DateTime? startsAt,
    DateTime? endsAt,
    DeadlineState? deadlineState,
    DateTime? previousStartsAt,
    String? externalCalendarId,
  }) => CalendarEvent(
    id: id,
    userId: userId,
    title: title,
    description: description,
    type: type,
    startsAt: startsAt ?? this.startsAt,
    endsAt: endsAt ?? this.endsAt,
    timezone: timezone,
    reminderMinutes: reminderMinutes,
    deadlineState: deadlineState ?? this.deadlineState,
    relatedEntityId: relatedEntityId,
    previousStartsAt: previousStartsAt ?? this.previousStartsAt,
    recurrence: recurrence,
    externalCalendarId: externalCalendarId ?? this.externalCalendarId,
    createdAt: createdAt,
  );
}

class CalendarConflict {
  const CalendarConflict({
    required this.firstEventId,
    required this.secondEventId,
    required this.overlap,
  });
  final String firstEventId;
  final String secondEventId;
  final Duration overlap;
}
