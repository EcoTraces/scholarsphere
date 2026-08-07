import 'package:flutter/material.dart';

import '../domain/background_job.dart';
import '../domain/job_queue_repository.dart';

class JobMonitorScreen extends StatefulWidget {
  const JobMonitorScreen({super.key, required this.repository});
  final JobQueueRepository repository;

  @override
  State<JobMonitorScreen> createState() => _JobMonitorScreenState();
}

class _JobMonitorScreenState extends State<JobMonitorScreen> {
  JobStatus? _status;
  late Future<List<BackgroundJob>> _jobs;
  void _reload() => _jobs = widget.repository.getJobs(status: _status);

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Background jobs'),
      actions: [
        IconButton(
          onPressed: () async {
            await widget.repository.processDue('admin-worker');
            if (mounted) setState(_reload);
          },
          tooltip: 'Process queued jobs',
          icon: const Icon(Icons.play_arrow),
        ),
      ],
    ),
    body: FutureBuilder<List<BackgroundJob>>(
      future: _jobs,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            DropdownButtonFormField<JobStatus?>(
              initialValue: _status,
              decoration: const InputDecoration(labelText: 'Job status'),
              items: [
                const DropdownMenuItem(
                  value: null,
                  child: Text('All statuses'),
                ),
                ...JobStatus.values.map(
                  (status) =>
                      DropdownMenuItem(value: status, child: Text(status.name)),
                ),
              ],
              onChanged: (status) {
                _status = status;
                setState(_reload);
              },
            ),
            const SizedBox(height: 20),
            for (final job in snapshot.data!)
              Card(
                child: ListTile(
                  leading: Icon(_icon(job.status)),
                  title: Text(job.type.name),
                  subtitle: Text(
                    '${job.status.name} | ${job.priority.name} priority | '
                    '${job.attempts}/${job.maxAttempts} attempts',
                  ),
                  trailing: PopupMenuButton<String>(
                    onSelected: (action) => _act(job, action),
                    itemBuilder: (_) => [
                      if ({
                        JobStatus.queued,
                        JobStatus.retrying,
                        JobStatus.processing,
                      }.contains(job.status))
                        const PopupMenuItem(
                          value: 'cancel',
                          child: Text('Cancel'),
                        ),
                      if ({
                        JobStatus.failed,
                        JobStatus.deadLettered,
                      }.contains(job.status))
                        const PopupMenuItem(
                          value: 'retry',
                          child: Text('Retry'),
                        ),
                    ],
                  ),
                ),
              ),
          ],
        );
      },
    ),
  );

  Future<void> _act(BackgroundJob job, String action) async {
    action == 'cancel'
        ? await widget.repository.cancel(job.id)
        : await widget.repository.retry(job.id);
    if (mounted) setState(_reload);
  }

  IconData _icon(JobStatus status) => switch (status) {
    JobStatus.completed => Icons.check_circle_outline,
    JobStatus.failed || JobStatus.deadLettered => Icons.error_outline,
    JobStatus.processing => Icons.sync,
    JobStatus.cancelled => Icons.cancel_outlined,
    _ => Icons.schedule,
  };
}
