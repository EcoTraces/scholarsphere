import 'package:flutter/material.dart';

import '../domain/source_record.dart';
import '../domain/source_registry_repository.dart';

class SourceRegistryScreen extends StatefulWidget {
  const SourceRegistryScreen({super.key, required this.repository});
  final SourceRegistryRepository repository;

  @override
  State<SourceRegistryScreen> createState() => _SourceRegistryScreenState();
}

class _SourceRegistryScreenState extends State<SourceRegistryScreen> {
  late Future<List<SourceRecord>> _sources;
  void _reload() => _sources = widget.repository.getAll();

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Source registry'),
      actions: [
        IconButton(
          onPressed: _add,
          tooltip: 'Register source',
          icon: const Icon(Icons.add_link),
        ),
      ],
    ),
    body: FutureBuilder<List<SourceRecord>>(
      future: _sources,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        return ListView(
          padding: const EdgeInsets.all(24),
          children: snapshot.data!.map((source) {
            return Card(
              child: ListTile(
                leading: CircleAvatar(
                  child: Text(source.trustLevel.name.toUpperCase()),
                ),
                title: Text(source.name),
                subtitle: Text(
                  '${source.domain} | Trust ${source.trustScore}/100 | ${source.verificationStatus.name}',
                ),
                trailing: PopupMenuButton<String>(
                  onSelected: (value) => _review(source, value == 'approve'),
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'approve', child: Text('Approve')),
                    PopupMenuItem(value: 'block', child: Text('Block')),
                  ],
                ),
              ),
            );
          }).toList(),
        );
      },
    ),
  );

  Future<void> _add() async {
    final name = TextEditingController();
    final domain = TextEditingController();
    final submitted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Register source'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              decoration: const InputDecoration(labelText: 'Source name'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: domain,
              decoration: const InputDecoration(labelText: 'Official domain'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Register'),
          ),
        ],
      ),
    );
    if (submitted != true ||
        name.text.trim().isEmpty ||
        domain.text.trim().isEmpty)
      return;
    final now = DateTime.now();
    await widget.repository.register(
      SourceRecord(
        id: 'source-${now.microsecondsSinceEpoch}',
        name: name.text.trim(),
        type: OpportunitySourceType.officialUniversityWebsite,
        domain: domain.text.trim(),
        country: 'Global',
        organizationId: '',
        trustLevel: ReliabilityLevel.e,
        trustScore: 0,
        verificationStatus: SourceVerificationStatus.pending,
        accuracyRate: 1,
        correctionCount: 0,
        rejectionCount: 0,
        isBlocked: false,
        createdAt: now,
        updatedAt: now,
      ),
    );
    if (mounted) setState(_reload);
  }

  Future<void> _review(SourceRecord source, bool approve) async {
    await widget.repository.review(
      sourceId: source.id,
      trustLevel: approve ? ReliabilityLevel.a : ReliabilityLevel.f,
      status: approve
          ? SourceVerificationStatus.approved
          : SourceVerificationStatus.blocked,
    );
    if (mounted) setState(_reload);
  }
}
