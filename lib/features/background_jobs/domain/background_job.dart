enum BackgroundJobType {
  deadlineChecking,
  notificationScheduling,
  emailDelivery,
  sourceAvailabilityCheck,
  opportunityReverification,
  expiredOpportunityDetection,
  recommendationGeneration,
  searchIndexUpdate,
  documentScanning,
  reportGeneration,
  dataCleanup,
  backupScheduling,
}

enum JobStatus {
  pending,
  queued,
  processing,
  completed,
  failed,
  retrying,
  cancelled,
  deadLettered,
}

enum JobPriority { low, normal, high, critical }

class BackgroundJob {
  const BackgroundJob({
    required this.id,
    required this.type,
    required this.payload,
    required this.priority,
    required this.status,
    required this.scheduledAt,
    required this.createdAt,
    required this.attempts,
    required this.maxAttempts,
    required this.correlationId,
    this.startedAt,
    this.completedAt,
    this.failureReason,
    this.workerId,
  });

  final String id;
  final BackgroundJobType type;
  final Map<String, Object?> payload;
  final JobPriority priority;
  final JobStatus status;
  final DateTime scheduledAt;
  final DateTime createdAt;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final int attempts;
  final int maxAttempts;
  final String? failureReason;
  final String? workerId;
  final String correlationId;

  BackgroundJob copyWith({
    JobStatus? status,
    DateTime? scheduledAt,
    DateTime? startedAt,
    DateTime? completedAt,
    int? attempts,
    String? failureReason,
    String? workerId,
  }) => BackgroundJob(
    id: id,
    type: type,
    payload: payload,
    priority: priority,
    status: status ?? this.status,
    scheduledAt: scheduledAt ?? this.scheduledAt,
    createdAt: createdAt,
    startedAt: startedAt ?? this.startedAt,
    completedAt: completedAt ?? this.completedAt,
    attempts: attempts ?? this.attempts,
    maxAttempts: maxAttempts,
    failureReason: failureReason ?? this.failureReason,
    workerId: workerId ?? this.workerId,
    correlationId: correlationId,
  );
}

class JobExecution {
  const JobExecution({
    required this.jobId,
    required this.workerId,
    required this.startedAt,
    required this.finishedAt,
    required this.status,
    this.failureReason,
  });
  final String jobId;
  final String workerId;
  final DateTime startedAt;
  final DateTime finishedAt;
  final JobStatus status;
  final String? failureReason;
}

class WorkerHealth {
  const WorkerHealth({
    required this.workerId,
    required this.lastHeartbeat,
    required this.processingJobIds,
    required this.healthy,
  });
  final String workerId;
  final DateTime lastHeartbeat;
  final Set<String> processingJobIds;
  final bool healthy;
}
