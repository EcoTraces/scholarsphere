import 'package:flutter/material.dart';

import '../domain/provider_analytics.dart';

class ProviderAnalyticsScreen extends StatelessWidget {
  const ProviderAnalyticsScreen({
    super.key,
    required this.providerId,
    required this.repository,
  });

  final String providerId;
  final ProviderAnalyticsRepository repository;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Opportunity analytics')),
    body: FutureBuilder<ProviderAnalyticsSnapshot>(
      future: repository.snapshot(providerId),
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final data = snapshot.data!;
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
                      'Engagement overview',
                      style: Theme.of(context).textTheme.headlineLarge,
                    ),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        _Metric(label: 'Views', value: data.views),
                        _Metric(label: 'Saves', value: data.saves),
                        _Metric(
                          label: 'Application clicks',
                          value: data.applicationClicks,
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    if (data.suppressed)
                      const ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(Icons.privacy_tip_outlined),
                        title: Text('Audience breakdown withheld'),
                        subtitle: Text(
                          'The audience is too small to show distributions '
                          'without increasing re-identification risk.',
                        ),
                      )
                    else ...[
                      _Breakdown(title: 'Countries', values: data.countries),
                      _Breakdown(
                        title: 'Academic levels',
                        values: data.studyLevels,
                      ),
                      _Breakdown(title: 'Fields', values: data.fields),
                    ],
                    const SizedBox(height: 16),
                    OutlinedButton.icon(
                      onPressed: () => _showExport(context),
                      icon: const Icon(Icons.download_outlined),
                      label: const Text('Export aggregate CSV'),
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

  Future<void> _showExport(BuildContext context) async {
    final csv = await repository.exportCsv(providerId);
    if (!context.mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Aggregate CSV export'),
        content: SelectableText(csv),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});
  final String label;
  final int value;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 190,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('$value', style: Theme.of(context).textTheme.headlineMedium),
            Text(label),
          ],
        ),
      ),
    ),
  );
}

class _Breakdown extends StatelessWidget {
  const _Breakdown({required this.title, required this.values});
  final String title;
  final Map<String, int> values;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 18),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        ...values.entries.map(
          (entry) => ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text(entry.key),
            trailing: Text('${entry.value}'),
          ),
        ),
      ],
    ),
  );
}
