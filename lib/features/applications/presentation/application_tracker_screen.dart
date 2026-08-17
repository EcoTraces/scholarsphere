import 'package:flutter/material.dart';

import '../domain/application_record.dart';
import '../domain/application_repository.dart';

class ApplicationTrackerScreen extends StatefulWidget {
  const ApplicationTrackerScreen({
    super.key,
    required this.userId,
    required this.repository,
    this.savedOnly = false,
  });

  final String userId;
  final ApplicationRepository repository;
  final bool savedOnly;

  @override
  State<ApplicationTrackerScreen> createState() =>
      _ApplicationTrackerScreenState();
}

class _ApplicationTrackerScreenState extends State<ApplicationTrackerScreen> {
  late Future<List<ApplicationRecord>> _records;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _records = widget.repository.getForUser(widget.userId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.savedOnly ? 'Saved opportunities' : 'Applications'),
      ),
      body: FutureBuilder<List<ApplicationRecord>>(
        future: _records,
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final records = snapshot.data!
              .where(
                (item) =>
                    !widget.savedOnly ||
                    item.stage == ApplicationStage.saved ||
                    item.stage == ApplicationStage.interested,
              )
              .toList();
          if (records.isEmpty) {
            return Center(
              child: Text(
                widget.savedOnly
                    ? 'No saved opportunities yet.'
                    : 'No applications are being tracked.',
              ),
            );
          }
          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 820),
                  child: Column(
                    children: [
                      for (final record in records)
                        Card(
                          margin: const EdgeInsets.only(bottom: 12),
                          child: ListTile(
                            contentPadding: const EdgeInsets.all(16),
                            title: Text(record.opportunityTitle),
                            subtitle: Text(
                              '${record.provider}\n${record.stageLabel}',
                            ),
                            isThreeLine: true,
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () => _edit(record),
                          ),
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
  }

  Future<void> _edit(ApplicationRecord record) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (context) => ApplicationRecordScreen(
          record: record,
          repository: widget.repository,
        ),
      ),
    );
    if (mounted) setState(_reload);
  }
}

class ApplicationRecordScreen extends StatefulWidget {
  const ApplicationRecordScreen({
    super.key,
    required this.record,
    required this.repository,
  });

  final ApplicationRecord record;
  final ApplicationRepository repository;

  @override
  State<ApplicationRecordScreen> createState() =>
      _ApplicationRecordScreenState();
}

class _ApplicationRecordScreenState extends State<ApplicationRecordScreen> {
  late ApplicationStage _stage = widget.record.stage;
  late final Map<String, TextEditingController> _controllers = {
    'applicationDate': TextEditingController(
      text: _date(widget.record.applicationDate),
    ),
    'reference': TextEditingController(
      text: widget.record.applicationReferenceNumber,
    ),
    'missing': TextEditingController(
      text: widget.record.missingDocuments.join(', '),
    ),
    'interviewDate': TextEditingController(
      text: _date(widget.record.interviewDate),
    ),
    'notes': TextEditingController(text: widget.record.personalNotes),
    'resultDate': TextEditingController(text: _date(widget.record.resultDate)),
    'value': TextEditingController(
      text: widget.record.scholarshipValue?.toString(),
    ),
    'followUp': TextEditingController(
      text: widget.record.followUpActions.join(', '),
    ),
  };

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Application record')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.record.opportunityTitle,
                    style: Theme.of(context).textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 20),
                  DropdownButtonFormField<ApplicationStage>(
                    initialValue: _stage,
                    decoration: const InputDecoration(
                      labelText: 'Application stage',
                    ),
                    items: ApplicationStage.values
                        .map(
                          (stage) => DropdownMenuItem(
                            value: stage,
                            child: Text(_stageLabel(stage)),
                          ),
                        )
                        .toList(),
                    onChanged: (value) =>
                        setState(() => _stage = value ?? _stage),
                  ),
                  const SizedBox(height: 12),
                  _dateField('applicationDate', 'Application date'),
                  _field('reference', 'Application reference number'),
                  _field('missing', 'Missing documents'),
                  _dateField('interviewDate', 'Interview date'),
                  _field('notes', 'Personal notes', maxLines: 4),
                  _dateField('resultDate', 'Result date'),
                  _field(
                    'value',
                    'Scholarship value',
                    keyboardType: TextInputType.number,
                  ),
                  _field('followUp', 'Follow-up actions'),
                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      key: const Key('save-application'),
                      onPressed: _save,
                      icon: const Icon(Icons.save_outlined),
                      label: const Text('Save application'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _field(
    String key,
    String label, {
    int maxLines = 1,
    TextInputType? keyboardType,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: TextField(
      controller: _controllers[key],
      maxLines: maxLines,
      keyboardType: keyboardType,
      decoration: InputDecoration(
        labelText: label,
        helperText: {'missing', 'followUp'}.contains(key)
            ? 'Separate multiple values with commas'
            : null,
      ),
    ),
  );

  Widget _dateField(String key, String label) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: TextField(
      controller: _controllers[key],
      readOnly: true,
      decoration: InputDecoration(
        labelText: label,
        suffixIcon: const Icon(Icons.calendar_today_outlined),
      ),
      onTap: () async {
        final value = await showDatePicker(
          context: context,
          firstDate: DateTime(2000),
          lastDate: DateTime.now().add(const Duration(days: 3650)),
          initialDate: DateTime.now(),
        );
        if (value != null) _controllers[key]!.text = _date(value);
      },
    ),
  );

  Future<void> _save() async {
    await widget.repository.update(
      widget.record.copyWith(
        stage: _stage,
        applicationDate: _parsedDate('applicationDate'),
        applicationReferenceNumber: _value('reference'),
        missingDocuments: _list('missing'),
        interviewDate: _parsedDate('interviewDate'),
        personalNotes: _value('notes'),
        resultDate: _parsedDate('resultDate'),
        scholarshipValue: double.tryParse(_value('value')),
        followUpActions: _list('followUp'),
      ),
    );
    if (!mounted) return;
    Navigator.of(context).pop();
  }

  String _value(String key) => _controllers[key]!.text.trim();

  List<String> _list(String key) => _value(key)
      .split(',')
      .map((item) => item.trim())
      .where((item) => item.isNotEmpty)
      .toList();

  DateTime? _parsedDate(String key) {
    final value = _value(key);
    return value.isEmpty ? null : DateTime.parse(value);
  }

  static String _date(DateTime? date) => date == null
      ? ''
      : '${date.year.toString().padLeft(4, '0')}-'
            '${date.month.toString().padLeft(2, '0')}-'
            '${date.day.toString().padLeft(2, '0')}';

  static String _stageLabel(ApplicationStage stage) => switch (stage) {
    ApplicationStage.interested => 'Interested',
    ApplicationStage.saved => 'Saved',
    ApplicationStage.preparingDocuments => 'Preparing documents',
    ApplicationStage.applicationStarted => 'Application started',
    ApplicationStage.applicationSubmitted => 'Application submitted',
    ApplicationStage.interviewStage => 'Interview stage',
    ApplicationStage.waitingForDecision => 'Waiting for decision',
    ApplicationStage.accepted => 'Accepted',
    ApplicationStage.rejected => 'Rejected',
    ApplicationStage.withdrawn => 'Withdrawn',
  };
}
