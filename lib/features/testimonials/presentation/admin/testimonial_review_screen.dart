import 'package:flutter/material.dart';

import '../../domain/testimonial.dart';
import '../../domain/testimonial_repository.dart';

/// Phase 12 of the feature spec: the full admin review page. Every
/// action here (approve/reject/request changes/verify/feature/archive)
/// goes through the backend's own authorization and status-transition
/// rules (`app/services/testimonial_service.py`) - this screen never
/// trusts its own idea of what transition is valid, it just surfaces
/// whatever error the backend returns (e.g. "only approved stories can
/// be featured").
class TestimonialReviewScreen extends StatefulWidget {
  const TestimonialReviewScreen({
    super.key,
    required this.repository,
    required this.testimonialId,
  });

  final TestimonialRepository repository;
  final String testimonialId;

  @override
  State<TestimonialReviewScreen> createState() =>
      _TestimonialReviewScreenState();
}

class _TestimonialReviewScreenState extends State<TestimonialReviewScreen> {
  late Future<AdminTestimonial> _testimonial;
  Future<List<TestimonialModerationHistoryItem>>? _history;
  bool _busy = false;
  final _notesController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _testimonial = widget.repository.getForModeration(widget.testimonialId);
    _testimonial.then((testimonial) {
      if (!mounted) return;
      _notesController.text = testimonial.internalNotes ?? '';
      setState(() {
        _history = widget.repository.getModerationHistory(widget.testimonialId);
      });
    });
    setState(() {});
  }

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _runAction(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
      if (!mounted) return;
      _reload();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Action failed: $error')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<String?> _promptForReason(String title, String label) {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          maxLines: 3,
          autofocus: true,
          decoration: InputDecoration(labelText: label),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: controller.text.trim().isEmpty
                ? null
                : () => Navigator.of(context).pop(controller.text.trim()),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
  }

  Future<void> _approve() async {
    final reason = await _promptForReason(
      'Approve story',
      'Notes (visible in moderation history)',
    );
    if (reason == null) return;
    await _runAction(
      () => widget.repository.approve(widget.testimonialId, reason),
    );
  }

  Future<void> _reject() async {
    final reason = await _promptForReason(
      'Reject story',
      'Reason (shown to the applicant)',
    );
    if (reason == null) return;
    await _runAction(
      () => widget.repository.reject(widget.testimonialId, reason),
    );
  }

  Future<void> _requestChanges() async {
    final reason = await _promptForReason(
      'Request changes',
      'What needs to change (shown to the applicant)',
    );
    if (reason == null) return;
    await _runAction(
      () => widget.repository.requestChanges(widget.testimonialId, reason),
    );
  }

  Future<void> _verify() async {
    final methodController = TextEditingController();
    final notesController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Verify story'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: methodController,
              autofocus: true,
              decoration: const InputDecoration(
                labelText: 'Verification method (e.g. Award letter reviewed)',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: notesController,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Notes (optional, internal)',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: methodController.text.trim().isEmpty
                ? null
                : () => Navigator.of(context).pop(true),
            child: const Text('Verify'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await _runAction(
      () => widget.repository.verify(
        widget.testimonialId,
        methodController.text.trim(),
        notesController.text.trim().isEmpty
            ? null
            : notesController.text.trim(),
      ),
    );
  }

  Future<void> _archive() async {
    final reason = await _promptForReason(
      'Archive story',
      'Reason for archiving',
    );
    if (reason == null) return;
    await _runAction(
      () => widget.repository.archive(widget.testimonialId, reason),
    );
  }

  Future<void> _saveNotes() async {
    await _runAction(
      () => widget.repository.setInternalNotes(
        widget.testimonialId,
        _notesController.text.trim(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Review Success Story')),
      body: FutureBuilder<AdminTestimonial>(
        future: _testimonial,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return const Center(child: Text('Could not load this submission.'));
          }
          final testimonial = snapshot.data!;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _actionBar(testimonial),
              const SizedBox(height: 16),
              _sectionCard('Applicant', [
                _kv('Name', testimonial.fullName),
                _kv('User ID', testimonial.userId),
                _kv('Country', testimonial.country ?? 'Not provided'),
                _kv('University', testimonial.university ?? 'Not provided'),
                _kv('Program', testimonial.program ?? 'Not provided'),
              ]),
              _sectionCard('Opportunity', [
                _kv('Name', testimonial.opportunityName),
                _kv('Provider', testimonial.opportunityProvider),
                _kv('Type', testimonial.opportunityType),
                _kv('Outcome', testimonial.outcome.label),
                _kv('Year', testimonial.successYear?.toString() ?? 'N/A'),
              ]),
              _sectionCard('Testimonial', [
                _paragraph('Challenge', testimonial.challenge),
                _paragraph('Discovery', testimonial.discoveryStory),
                _paragraph('Preparation', testimonial.preparationStory),
                _paragraph('ScholarSphere Help', testimonial.scholarsphereHelp),
                _paragraph('Outcome', testimonial.outcomeNarrative),
                _paragraph('Impact', testimonial.impact),
                _paragraph('Advice', testimonial.advice),
              ]),
              _sectionCard('Privacy Settings', [
                _kv('Display mode', testimonial.displayMode.label),
                _kv(
                  'Show university',
                  testimonial.showUniversity ? 'Yes' : 'No',
                ),
                _kv('Show country', testimonial.showCountry ? 'Yes' : 'No'),
                _kv('Show program', testimonial.showProgram ? 'Yes' : 'No'),
                _kv('Show photo', testimonial.showPhoto ? 'Yes' : 'No'),
              ]),
              _sectionCard('Evidence', [
                if (testimonial.evidenceStoragePaths.isEmpty)
                  const Text('No evidence uploaded.')
                else
                  for (final path in testimonial.evidenceStoragePaths)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.description_outlined),
                      title: Text(path.split('/').last),
                      trailing: TextButton(
                        onPressed: () async {
                          final url = await widget.repository
                              .getAdminEvidenceUrl(widget.testimonialId, path);
                          if (!context.mounted) return;
                          showDialog<void>(
                            context: context,
                            builder: (context) => AlertDialog(
                              title: const Text('Evidence link'),
                              content: SelectableText(url),
                              actions: [
                                TextButton(
                                  onPressed: () => Navigator.of(context).pop(),
                                  child: const Text('Close'),
                                ),
                              ],
                            ),
                          );
                        },
                        child: const Text('View'),
                      ),
                    ),
              ]),
              _sectionCard('Verification', [
                _kv('Status', testimonial.verificationStatus.name),
                _kv('Verified by', testimonial.verifiedBy ?? 'Not verified'),
                _kv(
                  'Verification method',
                  testimonial.verificationMethod ?? 'N/A',
                ),
              ]),
              _sectionCard('Internal Notes (staff-only)', [
                TextField(
                  controller: _notesController,
                  maxLines: 4,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    hintText: 'Working notes for other moderators...',
                  ),
                ),
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerRight,
                  child: OutlinedButton(
                    onPressed: _busy ? null : _saveNotes,
                    child: const Text('Save notes'),
                  ),
                ),
              ]),
              _sectionCard('Moderation History', [
                if (_history == null)
                  const SizedBox.shrink()
                else
                  FutureBuilder<List<TestimonialModerationHistoryItem>>(
                    future: _history,
                    builder: (context, historySnapshot) {
                      final items = historySnapshot.data ?? const [];
                      if (items.isEmpty) {
                        return const Text('No moderation actions yet.');
                      }
                      return Column(
                        children: [
                          for (final item in items)
                            ListTile(
                              contentPadding: EdgeInsets.zero,
                              title: Text(
                                '${item.previousStatus} -> ${item.newStatus}',
                              ),
                              subtitle: Text(
                                '${item.notes}\nby ${item.actorId}',
                              ),
                              isThreeLine: true,
                            ),
                        ],
                      );
                    },
                  ),
              ]),
            ],
          );
        },
      ),
    );
  }

  Widget _actionBar(AdminTestimonial testimonial) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        FilledButton(
          onPressed: _busy ? null : _approve,
          child: const Text('Approve'),
        ),
        OutlinedButton(
          onPressed: _busy ? null : _reject,
          child: const Text('Reject'),
        ),
        OutlinedButton(
          onPressed: _busy ? null : _requestChanges,
          child: const Text('Request Changes'),
        ),
        OutlinedButton(
          onPressed: _busy ? null : _verify,
          child: const Text('Verify'),
        ),
        OutlinedButton(
          onPressed: _busy
              ? null
              : () => _runAction(
                  () => testimonial.featured
                      ? widget.repository.unfeature(widget.testimonialId)
                      : widget.repository.feature(widget.testimonialId),
                ),
          child: Text(testimonial.featured ? 'Unfeature' : 'Feature'),
        ),
        OutlinedButton(
          onPressed: _busy ? null : _archive,
          child: const Text('Archive'),
        ),
      ],
    );
  }

  Widget _sectionCard(String title, List<Widget> children) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 10),
              ...children,
            ],
          ),
        ),
      ),
    );
  }

  Widget _kv(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 2),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 140,
          child: Text(label, style: const TextStyle(color: Colors.grey)),
        ),
        Expanded(child: Text(value)),
      ],
    ),
  );

  Widget _paragraph(String label, String? value) {
    if (value == null || value.trim().isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
          Text(value),
        ],
      ),
    );
  }
}
