import 'package:flutter/material.dart';

import '../data/live_opportunity.dart';
import '../data/live_opportunity_repository.dart';

/// Browses real, human-verified opportunities collected from Grants.gov,
/// Simpler.Grants.gov and the EU Funding & Tenders portal via the live
/// ScholarSphere backend. Distinct from the main Discover screen, which
/// still runs on illustrative demo data - see the engineering report for
/// why these are not yet merged.
class LiveOpportunitiesScreen extends StatefulWidget {
  const LiveOpportunitiesScreen({super.key, required this.repository});

  final LiveOpportunityRepository repository;

  @override
  State<LiveOpportunitiesScreen> createState() =>
      _LiveOpportunitiesScreenState();
}

class _LiveOpportunitiesScreenState extends State<LiveOpportunitiesScreen> {
  late Future<LiveOpportunityPage> _page;
  final _keywordController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _keywordController.dispose();
    super.dispose();
  }

  void _load() {
    _page = widget.repository.getPublished(
      keyword: _keywordController.text.trim().isEmpty
          ? null
          : _keywordController.text.trim(),
      pageSize: 50,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Live Opportunities (Beta)')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 900),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _SourceDisclaimer(),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _keywordController,
                          decoration: const InputDecoration(
                            prefixIcon: Icon(Icons.search),
                            hintText: 'Search real grants and funding calls',
                          ),
                          onSubmitted: (_) => setState(_load),
                        ),
                      ),
                      const SizedBox(width: 12),
                      FilledButton(
                        onPressed: () => setState(_load),
                        child: const Text('Search'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  FutureBuilder<LiveOpportunityPage>(
                    future: _page,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState ==
                          ConnectionState.waiting) {
                        return const Padding(
                          padding: EdgeInsets.symmetric(vertical: 48),
                          child: Center(child: CircularProgressIndicator()),
                        );
                      }
                      if (snapshot.hasError) {
                        return _ErrorPanel(error: snapshot.error!);
                      }
                      final page = snapshot.data!;
                      if (page.items.isEmpty) {
                        return const Padding(
                          padding: EdgeInsets.symmetric(vertical: 48),
                          child: Center(
                            child: Text(
                              'No published opportunities match this search.',
                            ),
                          ),
                        );
                      }
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${page.total} published, verified opportunities'),
                          const SizedBox(height: 12),
                          ...page.items.map(
                            (item) => _OpportunityCard(
                              opportunity: item,
                              onTap: () => Navigator.of(context).push<void>(
                                MaterialPageRoute(
                                  builder: (_) => LiveOpportunityDetailScreen(
                                    opportunity: item,
                                    repository: widget.repository,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SourceDisclaimer extends StatelessWidget {
  const _SourceDisclaimer();

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: const Color(0xFFEAF1FF),
      borderRadius: BorderRadius.circular(10),
    ),
    child: const Text(
      'Collected from official Grants.gov, Simpler.Grants.gov and EU '
      'Funding & Tenders records, then human-verified before appearing '
      'here. These are institutional grants and funding calls, not '
      'individual scholarships. Meeting the published criteria does not '
      'guarantee funding - review the official source before applying.',
      style: TextStyle(fontSize: 13, height: 1.4),
    ),
  );
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.error});
  final Object error;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.error.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(10),
    ),
    child: Row(
      children: [
        Icon(Icons.error_outline, color: Theme.of(context).colorScheme.error),
        const SizedBox(width: 10),
        Expanded(child: Text('$error')),
      ],
    ),
  );
}

class _OpportunityCard extends StatelessWidget {
  const _OpportunityCard({required this.opportunity, required this.onTap});
  final LiveOpportunity opportunity;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 12),
    child: InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (opportunity.isVerified) const _VerifiedBadge(),
                const Spacer(),
                _DeadlineBadge(
                  priority: opportunity.deadlinePriority,
                  daysRemaining: opportunity.daysRemaining,
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              opportunity.title,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 4),
            Text('${opportunity.providerName} | ${opportunity.country ?? 'Country not specified by source'}'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 16,
              runSpacing: 6,
              children: [
                _fact(context, 'Award', opportunity.awardRangeLabel),
                _fact(
                  context,
                  'Deadline',
                  opportunity.deadline == null
                      ? 'Not specified by source'
                      : _formatDate(opportunity.deadline!),
                ),
                _fact(context, 'Source', opportunity.sourceName),
              ],
            ),
          ],
        ),
      ),
    ),
  );

  Widget _fact(BuildContext context, String label, String value) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label.toUpperCase(),
        style: const TextStyle(fontSize: 10, color: Color(0xFF98A2B3)),
      ),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
    ],
  );
}

class _VerifiedBadge extends StatelessWidget {
  const _VerifiedBadge();

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: BoxDecoration(
      color: const Color(0xFF0B6E61).withValues(alpha: 0.12),
      borderRadius: BorderRadius.circular(20),
    ),
    child: const Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.verified, size: 14, color: Color(0xFF0B6E61)),
        SizedBox(width: 4),
        Text(
          'VERIFIED',
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w700,
            color: Color(0xFF0B6E61),
          ),
        ),
      ],
    ),
  );
}

class _DeadlineBadge extends StatelessWidget {
  const _DeadlineBadge({required this.priority, required this.daysRemaining});
  final DeadlinePriority priority;
  final int? daysRemaining;

  Color get _color => switch (priority) {
    DeadlinePriority.expired => const Color(0xFF98A2B3),
    DeadlinePriority.lastChance || DeadlinePriority.critical => const Color(
      0xFFD92D20,
    ),
    DeadlinePriority.urgent => const Color(0xFFFF7A21),
    DeadlinePriority.important => const Color(0xFFB54708),
    DeadlinePriority.upcoming => const Color(0xFF1769FF),
    DeadlinePriority.normal => const Color(0xFF0B6E61),
    DeadlinePriority.unknown => const Color(0xFF98A2B3),
  };

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: BoxDecoration(
      color: _color.withValues(alpha: 0.12),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Text(
      daysRemaining == null
          ? priority.label
          : daysRemaining! >= 0
          ? '${priority.label} ($daysRemaining d)'
          : priority.label,
      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: _color),
    ),
  );
}

class LiveOpportunityDetailScreen extends StatefulWidget {
  const LiveOpportunityDetailScreen({
    super.key,
    required this.opportunity,
    required this.repository,
  });

  final LiveOpportunity opportunity;
  final LiveOpportunityRepository repository;

  @override
  State<LiveOpportunityDetailScreen> createState() =>
      _LiveOpportunityDetailScreenState();
}

class _LiveOpportunityDetailScreenState
    extends State<LiveOpportunityDetailScreen> {
  late Future<LiveOpportunityEvidence> _evidence;
  late Future<List<VerificationHistoryItem>> _history;

  @override
  void initState() {
    super.initState();
    _evidence = widget.repository.getEvidence(widget.opportunity.id);
    _history = widget.repository.getVerificationHistory(widget.opportunity.id);
  }

  @override
  Widget build(BuildContext context) {
    final opportunity = widget.opportunity;
    return Scaffold(
      appBar: AppBar(title: Text(opportunity.title, maxLines: 1)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 800),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      if (opportunity.isVerified) const _VerifiedBadge(),
                      const SizedBox(width: 8),
                      _DeadlineBadge(
                        priority: opportunity.deadlinePriority,
                        daysRemaining: opportunity.daysRemaining,
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    opportunity.title,
                    style: Theme.of(context).textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 4),
                  Text('${opportunity.providerName} | ${opportunity.country ?? 'Country not specified by source'}'),
                  const SizedBox(height: 20),
                  _section(context, 'Description', opportunity.description ?? 'Not specified by source.'),
                  _keyValueRow('Opportunity type', opportunity.opportunityType),
                  _keyValueRow('Application status', opportunity.opportunityStatus),
                  _keyValueRow(
                    'Opening date',
                    opportunity.openingDate == null
                        ? 'Not specified by source'
                        : _formatDate(opportunity.openingDate!),
                  ),
                  _keyValueRow(
                    'Deadline',
                    opportunity.deadline == null
                        ? 'Not specified by source'
                        : _formatDate(opportunity.deadline!),
                  ),
                  _keyValueRow('Award', opportunity.awardRangeLabel),
                  _keyValueRow(
                    'Last verified',
                    opportunity.verifiedAt == null
                        ? 'Not yet verified'
                        : _formatDate(opportunity.verifiedAt!),
                  ),
                  const SizedBox(height: 12),
                  if (opportunity.officialSourceUrl != null)
                    SelectableText(
                      'Official source: ${opportunity.officialSourceUrl}',
                    ),
                  if (opportunity.officialApplicationUrl != null) ...[
                    const SizedBox(height: 4),
                    SelectableText(
                      'Official application: ${opportunity.officialApplicationUrl}',
                    ),
                  ],
                  const SizedBox(height: 24),
                  Text(
                    'Evidence',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Where each field above came from - the exact record '
                    'last collected from the official source.',
                  ),
                  const SizedBox(height: 12),
                  FutureBuilder<LiveOpportunityEvidence>(
                    future: _evidence,
                    builder: (context, snapshot) {
                      if (!snapshot.hasData) {
                        return const Padding(
                          padding: EdgeInsets.symmetric(vertical: 24),
                          child: Center(child: CircularProgressIndicator()),
                        );
                      }
                      return _EvidencePanel(evidence: snapshot.data!);
                    },
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Verification history',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 12),
                  FutureBuilder<List<VerificationHistoryItem>>(
                    future: _history,
                    builder: (context, snapshot) {
                      if (!snapshot.hasData) {
                        return const Padding(
                          padding: EdgeInsets.symmetric(vertical: 24),
                          child: Center(child: CircularProgressIndicator()),
                        );
                      }
                      final items = snapshot.data!;
                      if (items.isEmpty) {
                        return const Text('No verification history yet.');
                      }
                      return Column(
                        children: items
                            .map(
                              (item) => ListTile(
                                contentPadding: EdgeInsets.zero,
                                leading: const Icon(Icons.history),
                                title: Text(
                                  '${item.previousStatus} -> ${item.newStatus}',
                                ),
                                subtitle: Text(
                                  '${item.reason}\n${_formatDate(item.changedAt)}',
                                ),
                              ),
                            )
                            .toList(),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _section(BuildContext context, String title, String body) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 6),
        Text(body),
      ],
    ),
  );

  Widget _keyValueRow(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 160,
          child: Text(label, style: const TextStyle(color: Color(0xFF667085))),
        ),
        Expanded(child: Text(value)),
      ],
    ),
  );
}

class _EvidencePanel extends StatelessWidget {
  const _EvidencePanel({required this.evidence});
  final LiveOpportunityEvidence evidence;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: const Color(0xFFF7F8FA),
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: const Color(0xFFE1E6ED)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${evidence.sourceName} (${evidence.sourceType}, trust level: '
          '${evidence.sourceTrustLevel})',
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 4),
        Text('Collected: ${_formatDate(evidence.collectedAt)}'),
        const SizedBox(height: 12),
        ...evidence.fieldEvidence.map(
          (item) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 120,
                  child: Text(
                    item.field,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
                Expanded(child: Text('${item.value}')),
                Text(
                  item.confidence,
                  style: TextStyle(
                    fontSize: 11,
                    color: item.confidence == 'HIGH'
                        ? const Color(0xFF0B6E61)
                        : const Color(0xFF98A2B3),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        ExpansionTile(
          tilePadding: EdgeInsets.zero,
          title: const Text('Raw source record (as collected)'),
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFE1E6ED)),
              ),
              child: SelectableText(
                _prettyJson(evidence.rawPayload),
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

String _formatDate(DateTime date) =>
    '${date.day.toString().padLeft(2, '0')} '
    '${const [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ][date.month - 1]} '
    '${date.year}';

String _prettyJson(Map<String, dynamic> value, {int indent = 0}) {
  final buffer = StringBuffer();
  final pad = '  ' * indent;
  buffer.writeln('{');
  final entries = value.entries.toList();
  for (var index = 0; index < entries.length; index++) {
    final entry = entries[index];
    buffer.write('$pad  "${entry.key}": ');
    buffer.write(_prettyValue(entry.value, indent + 1));
    buffer.writeln(index == entries.length - 1 ? '' : ',');
  }
  buffer.write('$pad}');
  return buffer.toString();
}

String _prettyValue(dynamic value, int indent) {
  if (value is Map<String, dynamic>) return _prettyJson(value, indent: indent);
  if (value is List) {
    if (value.isEmpty) return '[]';
    final pad = '  ' * indent;
    final items = value.map((item) => '$pad  ${_prettyValue(item, indent + 1)}').join(',\n');
    return '[\n$items\n$pad]';
  }
  if (value is String) return '"$value"';
  return '$value';
}
