import '../domain/calendar_event.dart';
import '../domain/calendar_repository.dart';

class DemoCalendarRepository implements CalendarRepository {
  DemoCalendarRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final Map<String, CalendarEvent> _events = {};

  @override
  Future<CalendarEvent> save(CalendarEvent event) async {
    if (!event.endsAt.isAfter(event.startsAt)) {
      throw StateError('Calendar event end must follow its start.');
    }
    final saved = event.copyWith(
      deadlineState: _currentState(event.startsAt, event.deadlineState),
    );
    _events[event.id] = saved;
    return saved;
  }

  @override
  Future<CalendarEvent> updateDeadline(
    String eventId,
    DateTime newDeadline,
  ) async {
    final current = _require(eventId);
    final extended = newDeadline.isAfter(current.startsAt);
    final duration = current.endsAt.difference(current.startsAt);
    final updated = current.copyWith(
      previousStartsAt: current.startsAt,
      startsAt: newDeadline,
      endsAt: newDeadline.add(duration),
      deadlineState: extended ? DeadlineState.extended : DeadlineState.changed,
    );
    _events[eventId] = updated;
    return updated;
  }

  @override
  Future<List<CalendarEvent>> events(
    String userId, {
    DateTime? from,
    DateTime? to,
  }) async => _events.values.where((event) {
    return event.userId == userId &&
        (from == null || !event.endsAt.isBefore(from)) &&
        (to == null || !event.startsAt.isAfter(to));
  }).toList()..sort((a, b) => a.startsAt.compareTo(b.startsAt));

  @override
  Future<List<CalendarConflict>> conflicts(String userId) async {
    final values = await events(userId);
    final conflicts = <CalendarConflict>[];
    for (var left = 0; left < values.length; left++) {
      for (var right = left + 1; right < values.length; right++) {
        final start = values[left].startsAt.isAfter(values[right].startsAt)
            ? values[left].startsAt
            : values[right].startsAt;
        final end = values[left].endsAt.isBefore(values[right].endsAt)
            ? values[left].endsAt
            : values[right].endsAt;
        if (end.isAfter(start)) {
          conflicts.add(
            CalendarConflict(
              firstEventId: values[left].id,
              secondEventId: values[right].id,
              overlap: end.difference(start),
            ),
          );
        }
      }
    }
    return conflicts;
  }

  @override
  Future<String> exportIcs(String userId) async {
    final values = await events(userId);
    return [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//ScholarSphere//Deadline Calendar//EN',
      'CALSCALE:GREGORIAN',
      for (final event in values) ...[
        'BEGIN:VEVENT',
        'UID:${_escape(event.id)}@scholarsphere',
        'DTSTAMP:${_ics(event.createdAt)}',
        'DTSTART:${_ics(event.startsAt)}',
        'DTEND:${_ics(event.endsAt)}',
        'SUMMARY:${_escape(event.title)}',
        'DESCRIPTION:${_escape(event.description)}',
        if (event.recurrence != null)
          'RRULE:FREQ=${event.recurrence!.frequency.toUpperCase()};INTERVAL=${event.recurrence!.interval}'
              '${event.recurrence!.count == null ? '' : ';COUNT=${event.recurrence!.count}'}',
        'END:VEVENT',
      ],
      'END:VCALENDAR',
    ].join('\r\n');
  }

  @override
  Future<CalendarEvent> markSynchronized(
    String eventId,
    CalendarProvider provider,
    String externalId,
  ) async {
    final current = _require(eventId);
    final updated = current.copyWith(
      externalCalendarId: '${provider.name}:$externalId',
    );
    _events[eventId] = updated;
    return updated;
  }

  @override
  Future<List<CalendarEvent>> administrativeDeadlines() async =>
      _events.values
          .where((event) => event.type == CalendarEventType.opportunityDeadline)
          .toList()
        ..sort((a, b) => a.startsAt.compareTo(b.startsAt));

  CalendarEvent _require(String id) {
    final value = _events[id];
    if (value == null) throw StateError('Calendar event was not found.');
    return value;
  }

  String _ics(DateTime value) {
    final utc = value.toUtc();
    String two(int number) => number.toString().padLeft(2, '0');
    return '${utc.year}${two(utc.month)}${two(utc.day)}T'
        '${two(utc.hour)}${two(utc.minute)}${two(utc.second)}Z';
  }

  String _escape(String value) => value
      .replaceAll(r'\', r'\\')
      .replaceAll('\n', r'\n')
      .replaceAll(',', r'\,')
      .replaceAll(';', r'\;');

  DeadlineState _currentState(DateTime deadline, DeadlineState configured) {
    if ({
      DeadlineState.extended,
      DeadlineState.changed,
      DeadlineState.unconfirmed,
      DeadlineState.rollingDeadline,
    }.contains(configured)) {
      return configured;
    }
    final now = _clock();
    final date = DateTime(deadline.year, deadline.month, deadline.day);
    final today = DateTime(now.year, now.month, now.day);
    if (date == today) return DeadlineState.today;
    if (date.isBefore(today)) return DeadlineState.passed;
    if (date.difference(today).inDays <= 14) return DeadlineState.closingSoon;
    return DeadlineState.upcoming;
  }
}
