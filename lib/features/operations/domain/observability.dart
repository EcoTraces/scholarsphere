enum LogLevel { debug, info, warning, error, critical }

enum HealthStatus { healthy, degraded, unavailable }

enum IncidentStatus { open, acknowledged, investigating, resolved }

class ApplicationLog {
  const ApplicationLog({
    required this.id,
    required this.level,
    required this.service,
    required this.message,
    required this.timestamp,
    required this.correlationId,
    required this.context,
  });
  final String id;
  final LogLevel level;
  final String service;
  final String message;
  final DateTime timestamp;
  final String correlationId;
  final Map<String, Object?> context;
}

class MetricPoint {
  const MetricPoint({
    required this.name,
    required this.value,
    required this.unit,
    required this.timestamp,
    required this.labels,
  });
  final String name;
  final double value;
  final String unit;
  final DateTime timestamp;
  final Map<String, String> labels;
}

class TraceSpan {
  const TraceSpan({
    required this.traceId,
    required this.spanId,
    required this.operation,
    required this.service,
    required this.startedAt,
    required this.duration,
    required this.successful,
    this.parentSpanId,
  });
  final String traceId;
  final String spanId;
  final String? parentSpanId;
  final String operation;
  final String service;
  final DateTime startedAt;
  final Duration duration;
  final bool successful;
}

class ServiceHealth {
  const ServiceHealth({
    required this.service,
    required this.status,
    required this.checkedAt,
    required this.latencyMilliseconds,
    required this.details,
  });
  final String service;
  final HealthStatus status;
  final DateTime checkedAt;
  final int latencyMilliseconds;
  final Map<String, Object?> details;
}

class AlertRule {
  const AlertRule({
    required this.id,
    required this.metricName,
    required this.threshold,
    required this.comparison,
    required this.severity,
    required this.escalationTarget,
    required this.enabled,
  });
  final String id;
  final String metricName;
  final double threshold;
  final String comparison;
  final LogLevel severity;
  final String escalationTarget;
  final bool enabled;
}

class OperationalIncident {
  const OperationalIncident({
    required this.id,
    required this.title,
    required this.severity,
    required this.status,
    required this.createdAt,
    required this.escalationTarget,
    required this.notes,
  });
  final String id;
  final String title;
  final LogLevel severity;
  final IncidentStatus status;
  final DateTime createdAt;
  final String escalationTarget;
  final List<String> notes;
}

class PerformanceReport {
  const PerformanceReport({
    required this.requestVolume,
    required this.errorRate,
    required this.averageResponseMilliseconds,
    required this.metrics,
    required this.generatedAt,
  });
  final int requestVolume;
  final double errorRate;
  final double averageResponseMilliseconds;
  final Map<String, double> metrics;
  final DateTime generatedAt;
}
