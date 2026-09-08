import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../domain/moderation_case.dart';
import '../domain/moderation_repository.dart';

class ModerationQueueScreen extends StatefulWidget {
  const ModerationQueueScreen({
    super.key,
    required this.user,
    required this.repository,
    required this.onSignOut,
  });
  final UserAccount user;
  final ModerationRepository repository;
  final VoidCallback onSignOut;

  @override
  State<ModerationQueueScreen> createState() => _ModerationQueueScreenState();
}

class _ModerationQueueScreenState extends State<ModerationQueueScreen> {
  late Future<List<ModerationCase>> _queue;
  void _reload() => _queue = widget.repository.getQueue();

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Content moderation'),
      actions: [
        IconButton(
          onPressed: widget.onSignOut,
          tooltip: 'Sign out',
          icon: const Icon(Icons.logout),
        ),
      ],
    ),
    body: FutureBuilder<List<ModerationCase>>(
      future: _queue,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        return ListView(
          padding: const EdgeInsets.all(24),
          children: snapshot.data!
              .map(
                (report) => Card(
                  child: ListTile(
                    leading: const Icon(Icons.flag_outlined),
                    title: Text(_label(report.reportType.name)),
                    subtitle: Text(
                      '${report.entityType.name}: ${report.entityId}\n'
                      '${report.description}',
                    ),
                    isThreeLine: true,
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => _review(report),
                  ),
                ),
              )
              .toList(),
        );
      },
    ),
  );

  Future<void> _review(ModerationCase report) async {
    final action = await showModalBottomSheet<ModerationStatus>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.visibility_off_outlined),
              title: const Text('Review and temporarily hide'),
              onTap: () => Navigator.pop(context, ModerationStatus.underReview),
            ),
            ListTile(
              leading: const Icon(Icons.upload_file_outlined),
              title: const Text('Request evidence'),
              onTap: () =>
                  Navigator.pop(context, ModerationStatus.evidenceRequired),
            ),
            ListTile(
              leading: const Icon(Icons.escalator_warning_outlined),
              title: const Text('Escalate'),
              onTap: () => Navigator.pop(context, ModerationStatus.escalated),
            ),
            ListTile(
              leading: const Icon(Icons.delete_outline),
              title: const Text('Remove content'),
              onTap: () =>
                  Navigator.pop(context, ModerationStatus.contentRemoved),
            ),
            ListTile(
              leading: const Icon(Icons.check_circle_outline),
              title: const Text('Resolve'),
              onTap: () => Navigator.pop(context, ModerationStatus.resolved),
            ),
          ],
        ),
      ),
    );
    if (action == null) return;
    try {
      await widget.repository.transition(
        caseId: report.id,
        actorId: widget.user.id,
        status: action,
        notes: 'Moderator action: ${_label(action.name)}.',
        hideContent: action == ModerationStatus.underReview,
      );
      if (mounted) {
        setState(_reload);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Case marked as ${_label(action.name)}.')),
        );
      }
    } on ModerationFailure catch (failure) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(failure.message)));
      }
    }
  }

  static String _label(String value) => value.replaceAllMapped(
    RegExp(r'([A-Z])'),
    (match) => ' ${match.group(1)!.toLowerCase()}',
  );
}
