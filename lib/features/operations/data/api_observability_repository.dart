import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/observability.dart';
import '../domain/observability_repository.dart';

/// Reads and writes real logs, metrics, traces, alert rules, and incidents
/// from the ScholarSphere Python backend. Live replacement for
/// [DemoObservabilityRepository].
///
/// [registerHealthCheck] is a deliberate client-side no-op: it registers
/// an in-process Dart closure, which a Python backend has no way to
/// execute. [health] instead reports genuine signals for the services the
/// server can actually observe (database connectivity, the API process
/// itself) rather than faking the closure registry - see
/// `app/api/routes/observability.py`'s `health` handler for the
/// server-side half of this trade-off.
class ApiObservabilityRepository implements ObservabilityRepository {
  ApiObservabilityRepository({
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
  Future<void> log(ApplicationLog log) async {
    await _post('/observability/logs', {
      'level': log.level.name,
      'service': log.service,
      'message': log.message,
      'timestamp': log.timestamp.toUtc().toIso8601String(),
      'correlation_id': log.correlationId,
      'context': log.context,
    });
  }

  @override
  Future<void> metric(MetricPoint metric) async {
    await _post('/observability/metrics', {
      'name': metric.name,
      'value': metric.value,
      'unit': metric.unit,
      'timestamp': metric.timestamp.toUtc().toIso8601String(),
      'labels': metric.labels,
    });
  }

  @override
  Future<void> trace(TraceSpan span) async {
    await _post('/observability/traces', {
      'trace_id': span.traceId,
      'span_id': span.spanId,
      'parent_span_id': span.parentSpanId,
      'operation': span.operation,
      'service': span.service,
      'started_at': span.startedAt.toUtc().toIso8601String(),
      'duration_seconds': span.duration.inMicroseconds / 1000000,
      'successful': span.successful,
    });
  }

  @override
  Future<List<ApplicationLog>> searchLogs({
    LogLevel? minimumLevel,
    String? service,
    String? query,
  }) async {
    final body = await _get('/observability/logs', {
      if (minimumLevel != null) 'minimum_level': minimumLevel.name,
      if (service != null) 'service': service,
      if (query != null) 'query': query,
    });
    return (body as List<dynamic>)
        .map((item) => _toLog(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> registerHealthCheck(
    String service,
    Future<ServiceHealth> Function() check,
  ) async {}

  @override
  Future<List<ServiceHealth>> health() async {
    final body = await _get('/observability/health', const {});
    return (body as List<dynamic>)
        .map((item) => _toHealth(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> saveAlertRule(AlertRule rule) async {
    await _put('/observability/alert-rules/${Uri.encodeComponent(rule.id)}', {
      'id': rule.id,
      'metric_name': rule.metricName,
      'threshold': rule.threshold,
      'comparison': rule.comparison,
      'severity': rule.severity.name,
      'escalation_target': rule.escalationTarget,
      'enabled': rule.enabled,
    });
  }

  @override
  Future<List<OperationalIncident>> incidents() async {
    final body = await _get('/observability/incidents', const {});
    return (body as List<dynamic>)
        .map((item) => _toIncident(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<PerformanceReport> performanceReport() async {
    final body = await _get('/observability/performance-report', const {});
    final json = body as Map<String, dynamic>;
    return PerformanceReport(
      requestVolume: json['request_volume'] as int,
      errorRate: (json['error_rate'] as num).toDouble(),
      averageResponseMilliseconds:
          (json['average_response_milliseconds'] as num).toDouble(),
      metrics: (json['metrics'] as Map<String, dynamic>).map(
        (key, value) => MapEntry(key, (value as num).toDouble()),
      ),
      generatedAt: DateTime.parse(json['generated_at'] as String),
    );
  }

  @override
  Future<int> enforceLogRetention(Duration retention) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl/observability/logs/enforce-retention').replace(
      queryParameters: {'retention_seconds': '${retention.inSeconds}'},
    );
    final body = await _handle(() => _client.post(uri, headers: headers));
    return body as int;
  }

  ApplicationLog _toLog(Map<String, dynamic> json) => ApplicationLog(
    id: json['id'] as String,
    level: LogLevel.values.firstWhere((value) => value.name == json['level']),
    service: json['service'] as String,
    message: json['message'] as String,
    timestamp: DateTime.parse(json['timestamp'] as String),
    correlationId: json['correlation_id'] as String,
    context: Map<String, Object?>.from(
      json['context'] as Map<String, dynamic>,
    ),
  );

  ServiceHealth _toHealth(Map<String, dynamic> json) => ServiceHealth(
    service: json['service'] as String,
    status: HealthStatus.values.firstWhere(
      (value) => value.name == json['status'],
    ),
    checkedAt: DateTime.parse(json['checked_at'] as String),
    latencyMilliseconds: json['latency_milliseconds'] as int,
    details: Map<String, Object?>.from(
      json['details'] as Map<String, dynamic>,
    ),
  );

  OperationalIncident _toIncident(Map<String, dynamic> json) =>
      OperationalIncident(
        id: json['id'] as String,
        title: json['title'] as String,
        severity: LogLevel.values.firstWhere(
          (value) => value.name == json['severity'],
        ),
        status: IncidentStatus.values.firstWhere(
          (value) => value.name == json['status'],
        ),
        createdAt: DateTime.parse(json['created_at'] as String),
        escalationTarget: json['escalation_target'] as String,
        notes: (json['notes'] as List<dynamic>).cast<String>(),
      );

  Future<dynamic> _get(String path, Map<String, String> query) async {
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
