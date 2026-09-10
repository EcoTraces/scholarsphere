import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../opportunities/domain/opportunity.dart';
import '../data/api_verification_repository.dart';

/// The real verification queue, backed by the live FastAPI backend - not
/// demo data. Every action here (approve, reject, request re-verification,
/// mark expired, mark source unavailable, flag, add a note, edit a field)
/// calls a real, audited backend endpoint. See
/// [ApiVerificationRepository]'s class doc comment for why this is a
/// separate, simpler screen from the two-person-approval
/// [VerificationQueueScreen] used with demo data.
class LiveVerificationQueueScreen extends StatefulWidget {
  const LiveVerificationQueueScreen({
    super.key,
    required this.user,
    required this.repository,
    required this.onSignOut,
  });

  final UserAccount user;
  final ApiVerificationRepository repository;
  final VoidCallback onSignOut;

  @override
  State<LiveVerificationQueueScreen> createState() =>
      _LiveVerificationQueueScreenState();
}

class _LiveVerificationQueueScreenState
    extends State<LiveVerificationQueueScreen> {
  late Future<LiveVerificationQueueResult> _queue;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _queue = widget.repository.getLiveQueue();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Verification queue (live)'),
        actions: [
          IconButton(
            onPressed: () => setState(_reload),
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            onPressed: widget.onSignOut,
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: FutureBuilder<LiveVerificationQueueResult>(
        future: _queue,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return _ErrorPanel(
              error: snapshot.error,
              onRetry: () => setState(_reload),
            );
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final result = snapshot.data!;
          final queue = result.items;
          return ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 900),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Verification queue',
                        style: Theme.of(context).textTheme.headlineLarge,
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Opportunities imported from official sources, '
                        'awaiting a verification decision. Approval requires '
                        'every check below to pass.',
                      ),
                      const SizedBox(height: 24),
                      if (result.missingDeadlineCount > 0)
                        _MissingDeadlineBanner(
                          count: result.missingDeadlineCount,
                        ),
                      if (result.missingDeadlineCount > 0)
                        const SizedBox(height: 16),
                      if (queue.isEmpty && result.missingDeadlineCount == 0)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 48),
                          child: Center(
                            child: Text('The verification queue is clear.'),
                          ),
                        )
                      else
                        ...queue.map(
                          (item) => Card(
                            margin: const EdgeInsets.only(bottom: 12),
                            child: ListTile(
                              contentPadding: const EdgeInsets.all(16),
                              title: Text(item.title),
                              subtitle: Text(
                                '${item.provider} · deadline '
                                '${item.deadline.toLocal().toString().split(' ').first}',
                              ),
                              trailing: const Icon(Icons.chevron_right),
                              onTap: () => _review(item),
                            ),
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

  Future<void> _review(Opportunity opportunity) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (context) => LiveVerificationReviewScreen(
          opportunity: opportunity,
          officer: widget.user,
          repository: widget.repository,
        ),
      ),
    );
    if (changed == true && mounted) setState(_reload);
  }
}

class _MissingDeadlineBanner extends StatelessWidget {
  const _MissingDeadlineBanner({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: const Color(0xFFFFF4E5),
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: const Color(0xFFE09F3E)),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(Icons.info_outline, color: Color(0xFFE09F3E)),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            '$count more pending opportunit${count == 1 ? 'y is' : 'ies are'} '
            "missing a deadline from their source, so they can't be shown "
            'here for review yet.',
          ),
        ),
      ],
    ),
  );
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.error, required this.onRetry});

  final Object? error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final message = error is LiveBackendException
        ? (error! as LiveBackendException).message
        : 'Could not load the verification queue.';
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              color: Theme.of(context).colorScheme.error,
              size: 40,
            ),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}

const _decisions = <(String, String)>[
  ('approved', 'Approve (requires all checks)'),
  ('rejected', 'Reject'),
  ('reverification_required', 'Request re-verification'),
  ('expired', 'Mark expired'),
  ('source_unavailable', 'Mark source unavailable'),
  ('suspicious', 'Flag as suspicious'),
];

class LiveVerificationReviewScreen extends StatefulWidget {
  const LiveVerificationReviewScreen({
    super.key,
    required this.opportunity,
    required this.officer,
    required this.repository,
  });

  final Opportunity opportunity;
  final UserAccount officer;
  final ApiVerificationRepository repository;

  @override
  State<LiveVerificationReviewScreen> createState() =>
      _LiveVerificationReviewScreenState();
}

class _LiveVerificationReviewScreenState
    extends State<LiveVerificationReviewScreen> {
  bool _sourceChecked = false;
  bool _applicationLinkChecked = false;
  bool _deadlineChecked = false;
  bool _duplicateChecked = false;
  String _decision = 'approved';
  final _notes = TextEditingController();
  final _note = TextEditingController();
  bool _saving = false;
  bool _changed = false;
  String? _error;

  late Future<_ReviewContext> _context;

  @override
  void initState() {
    super.initState();
    _loadContext();
  }

  void _loadContext() => _context = _load();

  Future<_ReviewContext> _load() async {
    final evidenceFuture = widget.repository.getEvidence(widget.opportunity.id);
    final reviewFuture = widget.repository.getReviewState(
      widget.opportunity.id,
    );
    final historyFuture = widget.repository.getVerificationHistory(
      widget.opportunity.id,
    );
    final evidence = await evidenceFuture;
    final review = await reviewFuture;
    final history = await historyFuture;
    if (review != null) {
      _sourceChecked = review.sourceChecked;
      _applicationLinkChecked = review.applicationLinkChecked;
      _deadlineChecked = review.deadlineChecked;
      _duplicateChecked = review.duplicateChecked;
    }
    return _ReviewContext(evidence: evidence, review: review, history: history);
  }

  @override
  void dispose() {
    _notes.dispose();
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) Navigator.of(context).pop(_changed);
      },
      child: Scaffold(
        appBar: AppBar(title: const Text('Review opportunity')),
        body: FutureBuilder<_ReviewContext>(
          future: _context,
          builder: (context, snapshot) {
            if (!snapshot.hasData) {
              if (snapshot.hasError) {
                return _ErrorPanel(
                  error: snapshot.error,
                  onRetry: () => setState(_loadContext),
                );
              }
              return const Center(child: CircularProgressIndicator());
            }
            return _body(context, snapshot.data!);
          },
        ),
      ),
    );
  }

  Widget _body(BuildContext context, _ReviewContext data) => ListView(
    padding: const EdgeInsets.all(24),
    children: [
      Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.opportunity.title,
                style: Theme.of(context).textTheme.headlineLarge,
              ),
              const SizedBox(height: 8),
              Text(widget.opportunity.provider),
              const SizedBox(height: 20),
              _evidencePanel(context, data.evidence),
              const SizedBox(height: 24),
              Text(
                'Verification checklist',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 4),
              const Text(
                'All four must pass before this opportunity can be approved.',
              ),
              const SizedBox(height: 8),
              _check(
                'Official source checked',
                _sourceChecked,
                (value) => setState(() => _sourceChecked = value),
              ),
              _check(
                'Application link checked',
                _applicationLinkChecked,
                (value) => setState(() => _applicationLinkChecked = value),
              ),
              _check(
                'Deadline checked',
                _deadlineChecked,
                (value) => setState(() => _deadlineChecked = value),
              ),
              _check(
                'Checked for duplicates',
                _duplicateChecked,
                (value) => setState(() => _duplicateChecked = value),
              ),
              const SizedBox(height: 20),
              DropdownButtonFormField<String>(
                initialValue: _decision,
                decoration: const InputDecoration(labelText: 'Decision'),
                items: _decisions
                    .map(
                      (entry) => DropdownMenuItem(
                        value: entry.$1,
                        child: Text(entry.$2),
                      ),
                    )
                    .toList(),
                onChanged: (value) =>
                    setState(() => _decision = value ?? 'approved'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _notes,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'Reason for this decision',
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _saving ? null : _submitDecision,
                  icon: const Icon(Icons.fact_check_outlined),
                  label: Text(_saving ? 'Saving...' : 'Submit decision'),
                ),
              ),
              const Divider(height: 40),
              Text(
                'Add a note',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _note,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText:
                      'Timestamped officer note (does not change status)',
                ),
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: _saving ? null : _submitNote,
                icon: const Icon(Icons.note_add_outlined),
                label: const Text('Add note'),
              ),
              const Divider(height: 40),
              Text('History', style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 8),
              if (data.history.isEmpty)
                const Text('No history yet.')
              else
                ...data.history.reversed.map(
                  (entry) => Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      title: Text(
                        entry.isNoteOnly
                            ? 'Note added'
                            : '${entry.previousStatus} → ${entry.newStatus}',
                      ),
                      subtitle: Text(entry.reason),
                      trailing: Text(
                        entry.changedAt.toLocal().toString().split('.').first,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    ],
  );

  Widget _evidencePanel(
    BuildContext context,
    LiveOpportunityEvidence evidence,
  ) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Official source evidence',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 4),
          Text(
            '${evidence.sourceName} · trust level: '
            '${evidence.sourceTrustLevel}',
          ),
          if (evidence.officialSourceUrl != null) ...[
            const SizedBox(height: 8),
            SelectableText(evidence.officialSourceUrl!),
          ],
          const SizedBox(height: 12),
          ...evidence.fieldEvidence.map(
            (field) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                '${field.field}: ${field.value ?? 'not provided'} '
                '(${field.confidence})',
              ),
            ),
          ),
        ],
      ),
    ),
  );

  Widget _check(String label, bool value, ValueChanged<bool> update) =>
      CheckboxListTile(
        contentPadding: EdgeInsets.zero,
        value: value,
        title: Text(label),
        controlAffinity: ListTileControlAffinity.leading,
        onChanged: (checked) => update(checked ?? false),
      );

  Future<void> _submitDecision() async {
    if (_notes.text.trim().isEmpty) {
      setState(() => _error = 'A reason is required.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await widget.repository.submitDecision(
        opportunityId: widget.opportunity.id,
        decision: _decision,
        notes: _notes.text.trim(),
        sourceChecked: _sourceChecked,
        applicationLinkChecked: _applicationLinkChecked,
        deadlineChecked: _deadlineChecked,
        duplicateChecked: _duplicateChecked,
      );
      _changed = true;
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on LiveBackendException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _submitNote() async {
    if (_note.text.trim().isEmpty) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await widget.repository.addNote(widget.opportunity.id, _note.text.trim());
      _note.clear();
      _changed = true;
      if (mounted) setState(_loadContext);
    } on LiveBackendException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}

class _ReviewContext {
  const _ReviewContext({
    required this.evidence,
    required this.review,
    required this.history,
  });

  final LiveOpportunityEvidence evidence;
  final LiveVerificationReview? review;
  final List<LiveVerificationHistoryEntry> history;
}
