import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/calendar_event.dart';
import '../domain/calendar_repository.dart';

/// Reads and writes real deadline-calendar data from the ScholarSphere
/// Python backend. Live replacement for [DemoCalendarRepository]. The
/// `userId` parameters accepted by this interface are kept for signature
/// compatibility but not sent as the authorization scope: the backend
/// always scopes events to the caller's own verified uid.
class ApiCalendarRepository implements CalendarRepository {
  ApiCalendarRepository({
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
  Future<CalendarEvent> save(CalendarEvent event) async {
    try {
      final body = await _post('/calendar/events', {
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'type': _typeToWire(event.type),
        'starts_at': event.startsAt.toUtc().toIso8601String(),
        'ends_at': event.endsAt.toUtc().toIso8601String(),
        'timezone': event.timezone,
        'reminder_minutes': event.reminderMinutes.toList(),
        'deadline_state': _stateToWire(event.deadlineState),
        'related_entity_id': event.relatedEntityId,
        'recurrence': event.recurrence == null
            ? null
            : {
                'frequency': event.recurrence!.frequency,
                'interval': event.recurrence!.interval,
                'count': event.recurrence!.count,
                'until': event.recurrence!.until?.toUtc().toIso8601String(),
              },
      });
      return _toEvent(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 422) {
        throw StateError('Calendar event end must follow its start.');
      }
      rethrow;
    }
  }

  @override
  Future<CalendarEvent> updateDeadline(String eventId, DateTime newDeadline) async {
    try {
      final body = await _post('/calendar/events/$eventId/deadline', {
        'new_deadline': newDeadline.toUtc().toIso8601String(),
      });
      return _toEvent(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw StateError('Calendar event was not found.');
      }
      rethrow;
    }
  }

  @override
  Future<List<CalendarEvent>> events(
    String userId, {
    DateTime? from,
    DateTime? to,
  }) async {
    final query = <String, String>{
      if (from != null) 'from': from.toUtc().toIso8601String(),
      if (to != null) 'to': to.toUtc().toIso8601String(),
    };
    final body = await _get('/calendar/events', query);
    return (body as List<dynamic>)
        .map((item) => _toEvent(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<List<CalendarConflict>> conflicts(String userId) async {
    final body = await _get('/calendar/conflicts');
    return (body as List<dynamic>)
        .map(
          (item) => _toConflict(item as Map<String, dynamic>),
        )
        .toList();
  }

  @override
  Future<String> exportIcs(String userId) async {
    final body = await _get('/calendar/export.ics');
    return (body as Map<String, dynamic>)['content'] as String;
  }

  @override
  Future<CalendarEvent> markSynchronized(
    String eventId,
    CalendarProvider provider,
    String externalId,
  ) async {
    try {
      final body = await _post('/calendar/events/$eventId/sync', {
        'provider': provider.name,
        'external_id': externalId,
      });
      return _toEvent(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw StateError('Calendar event was not found.');
      }
      rethrow;
    }
  }

  @override
  Future<List<CalendarEvent>> administrativeDeadlines() async {
    final body = await _get('/calendar/administrative-deadlines');
    return (body as List<dynamic>)
        .map((item) => _toEvent(item as Map<String, dynamic>))
        .toList();
  }

  CalendarEvent _toEvent(Map<String, dynamic> json) => CalendarEvent(
    id: json['id'] as String,
    userId: json['user_id'] as String,
    title: json['title'] as String,
    description: json['description'] as String,
    type: _typeFromWire(json['type'] as String),
    startsAt: DateTime.parse(json['starts_at'] as String),
    endsAt: DateTime.parse(json['ends_at'] as String),
    timezone: json['timezone'] as String,
    reminderMinutes: (json['reminder_minutes'] as List<dynamic>)
        .cast<int>()
        .toSet(),
    deadlineState: _stateFromWire(json['deadline_state'] as String),
    relatedEntityId: json['related_entity_id'] as String?,
    createdAt: DateTime.parse(json['created_at'] as String),
    previousStartsAt: _dateTime(json['previous_starts_at']),
    recurrence: _toRecurrence(json['recurrence'] as Map<String, dynamic>?),
    externalCalendarId: json['external_calendar_id'] as String?,
  );

  CalendarConflict _toConflict(Map<String, dynamic> json) => CalendarConflict(
    firstEventId: json['first_event_id'] as String,
    secondEventId: json['second_event_id'] as String,
    overlap: Duration(seconds: json['overlap_seconds'] as int),
  );

  RecurrenceRule? _toRecurrence(Map<String, dynamic>? json) {
    if (json == null) return null;
    return RecurrenceRule(
      frequency: json['frequency'] as String,
      interval: json['interval'] as int,
      count: json['count'] as int?,
      until: _dateTime(json['until']),
    );
  }

  static DateTime? _dateTime(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  // Keep in sync with app/schemas/calendar.py's wire maps.
  static String _typeToWire(CalendarEventType type) => switch (type) {
    CalendarEventType.opportunityDeadline => 'opportunityDeadline',
    CalendarEventType.application => 'application',
    CalendarEventType.interview => 'interview',
    CalendarEventType.documentSubmission => 'documentSubmission',
    CalendarEventType.followUp => 'followUp',
  };

  static CalendarEventType _typeFromWire(String value) => switch (value) {
    'opportunityDeadline' => CalendarEventType.opportunityDeadline,
    'application' => CalendarEventType.application,
    'interview' => CalendarEventType.interview,
    'documentSubmission' => CalendarEventType.documentSubmission,
    'followUp' => CalendarEventType.followUp,
    _ => throw LiveBackendException('Unknown calendar event type: $value'),
  };

  static String _stateToWire(DeadlineState state) => switch (state) {
    DeadlineState.upcoming => 'upcoming',
    DeadlineState.closingSoon => 'closingSoon',
    DeadlineState.today => 'today',
    DeadlineState.passed => 'passed',
    DeadlineState.extended => 'extended',
    DeadlineState.changed => 'changed',
    DeadlineState.unconfirmed => 'unconfirmed',
    DeadlineState.rollingDeadline => 'rollingDeadline',
  };

  static DeadlineState _stateFromWire(String value) => switch (value) {
    'upcoming' => DeadlineState.upcoming,
    'closingSoon' => DeadlineState.closingSoon,
    'today' => DeadlineState.today,
    'passed' => DeadlineState.passed,
    'extended' => DeadlineState.extended,
    'changed' => DeadlineState.changed,
    'unconfirmed' => DeadlineState.unconfirmed,
    'rollingDeadline' => DeadlineState.rollingDeadline,
    _ => throw LiveBackendException('Unknown deadline state: $value'),
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
        'Sign-in expired. Sign in again.',
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
      throw const LiveBackendException('Sign in first.', statusCode: 401);
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
