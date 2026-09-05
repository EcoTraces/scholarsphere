import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../domain/security_backend_contracts.dart';
import '../domain/security_models.dart';
import '../domain/security_repository.dart';

/// Reads and writes real session, login-history, and alert data from the
/// ScholarSphere Python backend. Live replacement for
/// [DemoSecurityRepository].
///
/// [ensureLoginAllowed] is a deliberate client-side no-op rather than a
/// network call: the demo's brute-force lockout gate must run *before* a
/// credential is verified, when the caller has no Firebase ID token yet -
/// exposing that as an unauthenticated backend write would let anyone lock
/// an arbitrary victim's account by spamming fake failure records for
/// their email, a self-inflicted denial-of-service with no compensating
/// benefit given Firebase Authentication already throttles repeated
/// failed sign-ins itself. [recordLogin]/[createSession] remain fully
/// real and authenticated - they run *after* Firebase issues a token
/// (see [FirebaseAuthRepository]), so they're safe to expose and give the
/// security dashboard and "sign out everywhere" real data. The device's
/// `ipAddress` is always ignored client-side and derived by the server
/// from the request itself, never trusted from the caller.
class ApiSecurityRepository implements SecurityRepository {
  ApiSecurityRepository({
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
  Future<void> ensureLoginAllowed(String email, DeviceIdentity device) async {}

  @override
  Future<void> recordLogin({
    required String email,
    required LoginOutcome outcome,
    required DeviceIdentity device,
    String? userId,
  }) async {
    await _post('/security/login-history', {
      'outcome': _outcomeToWire(outcome),
      'device': _deviceToWire(device),
    });
  }

  @override
  Future<SecuritySession> createSession({
    required String userId,
    required DeviceIdentity device,
    required bool strongAuthentication,
    required bool privileged,
  }) async {
    try {
      final body = await _post('/security/sessions', {
        'device': _deviceToWire(device),
        'strong_authentication': strongAuthentication,
        'privileged': privileged,
      });
      return _toSession(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const SecurityFailure(
          'Privileged sessions require multi-factor authentication.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<void> revokeSession(String sessionId) async {
    await _delete('/security/sessions/$sessionId');
  }

  @override
  Future<void> revokeAllSessions(String userId) async {
    await _post('/security/users/$userId/sessions/revoke-all', const {});
  }

  @override
  Future<List<SecuritySession>> getSessions(String userId) async {
    final body = await _get('/security/sessions');
    return (body as List<dynamic>)
        .map((item) => _toSession(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<List<LoginHistoryEntry>> getLoginHistory(String email) async {
    final body = await _get('/security/login-history');
    return (body as List<dynamic>)
        .map((item) => _toHistoryEntry(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<List<SecurityAlert>> getAlerts(String userId) async {
    final body = await _get('/security/alerts');
    return (body as List<dynamic>)
        .map((item) => _toAlert(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> enforceRateLimit(String key, {int limit = 60}) async {
    try {
      await _post('/security/rate-limit-check', {'key': key, 'limit': limit});
    } on LiveBackendException catch (error) {
      if (error.statusCode == 429) {
        throw const SecurityFailure('Too many requests. Try again later.');
      }
      rethrow;
    }
  }

  static Map<String, dynamic> _deviceToWire(DeviceIdentity device) => {
    'id': device.id,
    'browser': device.browser,
    'operating_system': device.operatingSystem,
  };

  static DeviceIdentity _deviceFromWire(Map<String, dynamic> json) =>
      DeviceIdentity(
        id: json['id'] as String,
        browser: json['browser'] as String,
        operatingSystem: json['operating_system'] as String,
        ipAddress: json['ip_address'] as String,
      );

  SecuritySession _toSession(Map<String, dynamic> json) => SecuritySession(
    id: json['id'] as String,
    userId: json['user_id'] as String,
    device: _deviceFromWire(json['device'] as Map<String, dynamic>),
    createdAt: DateTime.parse(json['created_at'] as String),
    expiresAt: DateTime.parse(json['expires_at'] as String),
    lastActivityAt: DateTime.parse(json['last_activity_at'] as String),
    revokedAt: json['revoked_at'] == null
        ? null
        : DateTime.parse(json['revoked_at'] as String),
    strongAuthentication: json['strong_authentication'] as bool,
  );

  LoginHistoryEntry _toHistoryEntry(Map<String, dynamic> json) =>
      LoginHistoryEntry(
        id: json['id'] as String,
        email: json['email'] as String,
        occurredAt: DateTime.parse(json['occurred_at'] as String),
        outcome: _outcomeFromWire(json['outcome'] as String),
        device: _deviceFromWire(json['device'] as Map<String, dynamic>),
        suspicious: json['suspicious'] as bool,
      );

  SecurityAlert _toAlert(Map<String, dynamic> json) => SecurityAlert(
    id: json['id'] as String,
    userId: json['user_id'] as String?,
    type: _alertTypeFromWire(json['type'] as String),
    message: json['message'] as String,
    createdAt: DateTime.parse(json['created_at'] as String),
    acknowledgedAt: json['acknowledged_at'] == null
        ? null
        : DateTime.parse(json['acknowledged_at'] as String),
  );

  // Keep in sync with app/schemas/security.py's wire maps.
  static String _outcomeToWire(LoginOutcome outcome) => outcome.name;

  static LoginOutcome _outcomeFromWire(String value) =>
      LoginOutcome.values.firstWhere(
        (outcome) => outcome.name == value,
        orElse: () =>
            throw LiveBackendException('Unknown login outcome: $value'),
      );

  static SecurityAlertType _alertTypeFromWire(String value) =>
      SecurityAlertType.values.firstWhere(
        (type) => type.name == value,
        orElse: () =>
            throw LiveBackendException('Unknown security alert type: $value'),
      );

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

  Future<dynamic> _delete(String path) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(() => _client.delete(uri, headers: headers));
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
