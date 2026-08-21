import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/provider_analytics.dart';

/// Reads and writes real provider-engagement analytics from the
/// ScholarSphere Python backend. Live replacement for
/// [DemoProviderAnalyticsRepository].
///
/// [snapshot] and [exportCsv] are restricted server-side to a provider's
/// own owner/administrators (or staff), matching the access [_relationship]
/// check used for provider opportunity management. [record]'s `userId` is
/// only ever persisted when the caller explicitly sets
/// `identifiableSharingConsent`, and even then it is taken from the
/// caller's own verified auth token server-side, never trusted from the
/// client - a client-supplied `userId` on the event is not sent.
class ApiProviderAnalyticsRepository implements ProviderAnalyticsRepository {
  ApiProviderAnalyticsRepository({
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
  Future<void> record(EngagementEvent event) async {
    await _post('/provider-analytics/events', {
      'provider_id': event.providerId,
      'opportunity_id': event.opportunityId,
      'kind': event.kind,
      'country': event.country,
      'study_level': event.studyLevel,
      'field': event.field,
      'occurred_at': event.occurredAt.toUtc().toIso8601String(),
      'identifiable_sharing_consent': event.identifiableSharingConsent,
    });
  }

  @override
  Future<ProviderAnalyticsSnapshot> snapshot(String providerId) async {
    final body = await _get('/provider-analytics/$providerId/snapshot');
    final json = body as Map<String, dynamic>;
    return ProviderAnalyticsSnapshot(
      views: json['views'] as int,
      saves: json['saves'] as int,
      applicationClicks: json['application_clicks'] as int,
      countries: (json['countries'] as Map<String, dynamic>).map(
        (key, value) => MapEntry(key, value as int),
      ),
      studyLevels: (json['study_levels'] as Map<String, dynamic>).map(
        (key, value) => MapEntry(key, value as int),
      ),
      fields: (json['fields'] as Map<String, dynamic>).map(
        (key, value) => MapEntry(key, value as int),
      ),
      suppressed: json['suppressed'] as bool,
    );
  }

  @override
  Future<String> exportCsv(String providerId) async {
    final body = await _get('/provider-analytics/$providerId/export');
    return (body as Map<String, dynamic>)['csv'] as String;
  }

  Future<dynamic> _get(String path) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
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
