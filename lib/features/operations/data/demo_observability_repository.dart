import '../domain/observability.dart';
import '../domain/observability_repository.dart';

class DemoObservabilityRepository implements ObservabilityRepository {
  DemoObservabilityRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final List<ApplicationLog> _logs = [];
  final List<MetricPoint> _metrics = [];
  final List<TraceSpan> _traces = [];
  final Map<String, Future<ServiceHealth> Function()> _healthChecks = {};
  final Map<String, AlertRule> _rules = {};
  final List<OperationalIncident> _incidents = [];

  @override
  Future<void> log(ApplicationLog log) async => _logs.add(log);

  @override
  Future<void> metric(MetricPoint metric) async {
    _metrics.add(metric);
    for (final rule in _rules.values.where(
      (rule) => rule.enabled && rule.metricName == metric.name,
    )) {
      final triggered = rule.comparison == 'greaterThan'
          ? metric.value > rule.threshold
          : metric.value < rule.threshold;
      if (triggered) {
        _incidents.add(
          OperationalIncident(
            id: 'incident-${_clock().microsecondsSinceEpoch}',
            title: '${metric.name} crossed ${rule.threshold}',
            severity: rule.severity,
            status: IncidentStatus.open,
            createdAt: _clock(),
            escalationTarget: rule.escalationTarget,
            notes: ['Observed value: ${metric.value} ${metric.unit}'],
          ),
        );
      }
    }
  }

  @override
  Future<void> trace(TraceSpan span) async => _traces.add(span);

  @override
  Future<List<ApplicationLog>> searchLogs({
    LogLevel? minimumLevel,
    String? service,
    String? query,
  }) async {
    final normalized = query?.toLowerCase();
    return _logs.where((log) {
      return (minimumLevel == null || log.level.index >= minimumLevel.index) &&
          (service == null || log.service == service) &&
          (normalized == null ||
              log.message.toLowerCase().contains(normalized) ||
              log.correlationId.toLowerCase().contains(normalized));
    }).toList();
  }

  @override
  Future<void> registerHealthCheck(
    String service,
    Future<ServiceHealth> Function() check,
  ) async {
    _healthChecks[service] = check;
  }

  @override
  Future<List<ServiceHealth>> health() async {
    final results = <ServiceHealth>[];
    for (final entry in _healthChecks.entries) {
      try {
        results.add(await entry.value());
      } catch (error) {
        results.add(
          ServiceHealth(
            service: entry.key,
            status: HealthStatus.unavailable,
            checkedAt: _clock(),
            latencyMilliseconds: 0,
            details: {'error': error.toString()},
          ),
        );
      }
    }
    return results;
  }

  @override
  Future<void> saveAlertRule(AlertRule rule) async {
    _rules[rule.id] = rule;
  }

  @override
  Future<List<OperationalIncident>> incidents() async =>
      List.unmodifiable(_incidents);

  @override
  Future<PerformanceReport> performanceReport() async {
    final requestMetrics = _metrics.where(
      (metric) => metric.name == 'request.duration_ms',
    );
    final errors = _metrics.where((metric) => metric.name == 'request.error');
    final latest = <String, double>{};
    for (final metric in _metrics) {
      latest[metric.name] = metric.value;
    }
    return PerformanceReport(
      requestVolume: requestMetrics.length,
      errorRate: requestMetrics.isEmpty
          ? 0
          : errors.length / requestMetrics.length,
      averageResponseMilliseconds: requestMetrics.isEmpty
          ? 0
          : requestMetrics
                    .map((metric) => metric.value)
                    .reduce((a, b) => a + b) /
                requestMetrics.length,
      metrics: latest,
      generatedAt: _clock(),
    );
  }

  @override
  Future<int> enforceLogRetention(Duration retention) async {
    final cutoff = _clock().subtract(retention);
    final before = _logs.length;
    _logs.removeWhere((log) => log.timestamp.isBefore(cutoff));
    return before - _logs.length;
  }
}
