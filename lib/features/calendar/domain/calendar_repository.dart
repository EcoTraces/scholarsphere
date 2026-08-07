import 'calendar_event.dart';

abstract class CalendarRepository {
  Future<CalendarEvent> save(CalendarEvent event);
  Future<CalendarEvent> updateDeadline(String eventId, DateTime newDeadline);
  Future<List<CalendarEvent>> events(
    String userId, {
    DateTime? from,
    DateTime? to,
  });
  Future<List<CalendarConflict>> conflicts(String userId);
  Future<String> exportIcs(String userId);
  Future<CalendarEvent> markSynchronized(
    String eventId,
    CalendarProvider provider,
    String externalId,
  );
  Future<List<CalendarEvent>> administrativeDeadlines();
}
