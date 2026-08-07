import '../domain/background_job.dart';
import '../domain/job_queue_repository.dart';

class DemoJobQueueRepository implements JobQueueRepository {
  DemoJobQueueRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final Map<String, BackgroundJob> _jobs = {};
  final Map<BackgroundJobType, JobHandler> _handlers = {};
  final Map<String, String> _deduplication = {};
  final List<JobExecution> _history = [];
  final Map<String, DateTime> _heartbeats = {};

  @override
  Future<BackgroundJob> enqueue({
    required BackgroundJobType type,
    required Map<String, Object?> payload,
    JobPriority priority = JobPriority.normal,
    DateTime? scheduledAt,
    int maxAttempts = 3,
    String? deduplicationKey,
    String? correlationId,
  }) async {
    if (maxAttempts < 1) {
      throw const JobQueueFailure('A job requires at least one attempt.');
    }
    if (deduplicationKey != null) {
      final existingId = _deduplication[deduplicationKey];
      final existing = _jobs[existingId];
      if (existing != null &&
          !{
            JobStatus.completed,
            JobStatus.cancelled,
            JobStatus.deadLettered,
          }.contains(existing.status)) {
        return existing;
      }
    }
    final now = _clock();
    final job = BackgroundJob(
      id: 'job-${now.microsecondsSinceEpoch}-${_jobs.length}',
      type: type,
      payload: Map.unmodifiable(payload),
      priority: priority,
      status: JobStatus.queued,
      scheduledAt: scheduledAt ?? now,
      createdAt: now,
      attempts: 0,
      maxAttempts: maxAttempts,
      correlationId:
          correlationId ?? 'job-correlation-${now.microsecondsSinceEpoch}',
    );
    _jobs[job.id] = job;
    if (deduplicationKey != null) _deduplication[deduplicationKey] = job.id;
    return job;
  }

  @override
  void registerHandler(BackgroundJobType type, JobHandler handler) {
    _handlers[type] = handler;
  }

  @override
  Future<BackgroundJob?> processNext(String workerId) async {
    await heartbeat(workerId);
    final now = _clock();
    final candidates =
        _jobs.values
            .where(
              (job) =>
                  {JobStatus.queued, JobStatus.retrying}.contains(job.status) &&
                  !job.scheduledAt.isAfter(now),
            )
            .toList()
          ..sort((a, b) {
            final priority = b.priority.index.compareTo(a.priority.index);
            return priority != 0
                ? priority
                : a.scheduledAt.compareTo(b.scheduledAt);
          });
    if (candidates.isEmpty) return null;
    final job = candidates.first;
    final started = now;
    var current = job.copyWith(
      status: JobStatus.processing,
      startedAt: started,
      attempts: job.attempts + 1,
      workerId: workerId,
    );
    _jobs[job.id] = current;
    try {
      final handler = _handlers[job.type];
      if (handler == null) {
        throw const JobQueueFailure('No worker handler is registered.');
      }
      await handler(current);
      final finished = _clock();
      current = current.copyWith(
        status: JobStatus.completed,
        completedAt: finished,
      );
      _history.add(
        JobExecution(
          jobId: job.id,
          workerId: workerId,
          startedAt: started,
          finishedAt: finished,
          status: JobStatus.completed,
        ),
      );
    } catch (error) {
      final finished = _clock();
      final exhausted = current.attempts >= current.maxAttempts;
      current = current.copyWith(
        status: exhausted ? JobStatus.deadLettered : JobStatus.retrying,
        scheduledAt: finished.add(
          Duration(seconds: 1 << (current.attempts - 1).clamp(0, 6).toInt()),
        ),
        completedAt: finished,
        failureReason: error.toString(),
      );
      _history.add(
        JobExecution(
          jobId: job.id,
          workerId: workerId,
          startedAt: started,
          finishedAt: finished,
          status: current.status,
          failureReason: error.toString(),
        ),
      );
    }
    _jobs[job.id] = current;
    await heartbeat(workerId);
    return current;
  }

  @override
  Future<void> processDue(String workerId, {int limit = 20}) async {
    for (var count = 0; count < limit; count++) {
      final processed = await processNext(workerId);
      if (processed == null) return;
    }
  }

  @override
  Future<BackgroundJob> cancel(String jobId) async {
    final job = _require(jobId);
    if ({JobStatus.completed, JobStatus.deadLettered}.contains(job.status)) {
      throw const JobQueueFailure('This job can no longer be cancelled.');
    }
    final cancelled = job.copyWith(
      status: JobStatus.cancelled,
      completedAt: _clock(),
    );
    _jobs[jobId] = cancelled;
    return cancelled;
  }

  @override
  Future<BackgroundJob> retry(String jobId) async {
    final job = _require(jobId);
    if (!{JobStatus.failed, JobStatus.deadLettered}.contains(job.status)) {
      throw const JobQueueFailure('Only failed jobs can be retried.');
    }
    final retried = job.copyWith(
      status: JobStatus.retrying,
      attempts: 0,
      scheduledAt: _clock(),
    );
    _jobs[jobId] = retried;
    return retried;
  }

  @override
  Future<List<BackgroundJob>> getJobs({JobStatus? status}) async => _jobs.values
      .where((job) => status == null || job.status == status)
      .toList();

  @override
  Future<List<BackgroundJob>> getDeadLetters() async =>
      getJobs(status: JobStatus.deadLettered);

  @override
  Future<List<JobExecution>> getHistory(String jobId) async =>
      _history.where((entry) => entry.jobId == jobId).toList();

  @override
  Future<void> heartbeat(String workerId) async {
    _heartbeats[workerId] = _clock();
  }

  @override
  Future<List<WorkerHealth>> workerHealth() async {
    final now = _clock();
    return _heartbeats.entries
        .map(
          (entry) => WorkerHealth(
            workerId: entry.key,
            lastHeartbeat: entry.value,
            processingJobIds: _jobs.values
                .where(
                  (job) =>
                      job.workerId == entry.key &&
                      job.status == JobStatus.processing,
                )
                .map((job) => job.id)
                .toSet(),
            healthy: now.difference(entry.value) < const Duration(minutes: 2),
          ),
        )
        .toList();
  }

  BackgroundJob _require(String id) {
    final job = _jobs[id];
    if (job == null) throw const JobQueueFailure('Job was not found.');
    return job;
  }
}
