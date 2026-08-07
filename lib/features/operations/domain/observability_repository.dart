import 'observability.dart';

abstract class ObservabilityRepository {
  Future<void> log(ApplicationLog log);
  Future<void> metric(MetricPoint metric);
  Future<void> trace(TraceSpan span);
  Future<List<ApplicationLog>> searchLogs({
    LogLevel? minimumLevel,
    String? service,
    String? query,
  });
  Future<void> registerHealthCheck(
    String service,
    Future<ServiceHealth> Function() check,
  );
  Future<List<ServiceHealth>> health();
  Future<void> saveAlertRule(AlertRule rule);
  Future<List<OperationalIncident>> incidents();
  Future<PerformanceReport> performanceReport();
  Future<int> enforceLogRetention(Duration retention);
}
