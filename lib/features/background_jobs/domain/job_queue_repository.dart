import 'background_job.dart';

typedef JobHandler = Future<void> Function(BackgroundJob job);

abstract class JobQueueRepository {
  Future<BackgroundJob> enqueue({
    required BackgroundJobType type,
    required Map<String, Object?> payload,
    JobPriority priority = JobPriority.normal,
    DateTime? scheduledAt,
    int maxAttempts = 3,
    String? deduplicationKey,
    String? correlationId,
  });
  void registerHandler(BackgroundJobType type, JobHandler handler);
  Future<BackgroundJob?> processNext(String workerId);
  Future<void> processDue(String workerId, {int limit = 20});
  Future<BackgroundJob> cancel(String jobId);
  Future<BackgroundJob> retry(String jobId);
  Future<List<BackgroundJob>> getJobs({JobStatus? status});
  Future<List<BackgroundJob>> getDeadLetters();
  Future<List<JobExecution>> getHistory(String jobId);
  Future<void> heartbeat(String workerId);
  Future<List<WorkerHealth>> workerHealth();
}

class JobQueueFailure implements Exception {
  const JobQueueFailure(this.message);
  final String message;
}
