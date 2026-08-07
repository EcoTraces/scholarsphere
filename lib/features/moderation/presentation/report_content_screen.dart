import 'package:flutter/material.dart';

import '../domain/moderation_case.dart';
import '../domain/moderation_repository.dart';

class ReportContentScreen extends StatefulWidget {
  const ReportContentScreen({
    super.key,
    required this.reporterId,
    required this.entityType,
    required this.entityId,
    required this.repository,
  });

  final String reporterId;
  final ReportedEntityType entityType;
  final String entityId;
  final ModerationRepository repository;

  @override
  State<ReportContentScreen> createState() => _ReportContentScreenState();
}

class _ReportContentScreenState extends State<ReportContentScreen> {
  ModerationReportType _type = ModerationReportType.misleadingContent;
  final _description = TextEditingController();
  final _evidence = TextEditingController();
  String? _error;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Report content')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        DropdownButtonFormField<ModerationReportType>(
          initialValue: _type,
          decoration: const InputDecoration(labelText: 'Report type'),
          items: ModerationReportType.values
              .map(
                (value) => DropdownMenuItem(
                  value: value,
                  child: Text(_label(value.name)),
                ),
              )
              .toList(),
          onChanged: (value) => setState(() => _type = value ?? _type),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _description,
          maxLines: 4,
          decoration: const InputDecoration(
            labelText: 'What is wrong with this content?',
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _evidence,
          decoration: const InputDecoration(
            labelText: 'Evidence link or reference (optional)',
          ),
        ),
        if (_error != null) ...[
          const SizedBox(height: 12),
          Text(
            _error!,
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        ],
        const SizedBox(height: 24),
        FilledButton.icon(
          onPressed: _submit,
          icon: const Icon(Icons.flag_outlined),
          label: const Text('Submit report'),
        ),
      ],
    ),
  );

  Future<void> _submit() async {
    if (_description.text.trim().isEmpty) {
      setState(() => _error = 'A report description is required.');
      return;
    }
    final now = DateTime.now();
    try {
      await widget.repository.submit(
        ModerationCase(
          id: 'report-${now.microsecondsSinceEpoch}',
          reporterId: widget.reporterId,
          entityType: widget.entityType,
          entityId: widget.entityId,
          reportType: _type,
          description: _description.text.trim(),
          evidence: _evidence.text.trim().isEmpty
              ? const []
              : [
                  ModerationEvidence(
                    location: _evidence.text.trim(),
                    description: 'Reporter evidence',
                  ),
                ],
          status: ModerationStatus.submitted,
          createdAt: now,
          history: [
            ModerationHistoryEntry(
              status: ModerationStatus.submitted,
              actorId: widget.reporterId,
              notes: 'Report submitted.',
              createdAt: now,
            ),
          ],
        ),
      );
      if (mounted) Navigator.pop(context, true);
    } on ModerationFailure catch (failure) {
      if (mounted) setState(() => _error = failure.message);
    }
  }

  String _label(String value) => value.replaceAllMapped(
    RegExp(r'([A-Z])'),
    (match) => ' ${match.group(1)!.toLowerCase()}',
  );
}
