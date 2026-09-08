import 'package:flutter/material.dart';

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../opportunities/domain/opportunity.dart';
import '../data/api_verification_repository.dart';

/// Verified opportunities are never published automatically - publishing
/// is its own explicit, audited administrator decision, separate from a
/// verification officer's approval. This screen is that missing step:
/// list every verified-but-unpublished opportunity and let an
/// administrator put each one live for applicants (or take it back down).
class PublicationQueueScreen extends StatefulWidget {
  const PublicationQueueScreen({
    super.key,
    required this.repository,
    required this.onSignOut,
  });

  final ApiVerificationRepository repository;
  final VoidCallback onSignOut;

  @override
  State<PublicationQueueScreen> createState() => _PublicationQueueScreenState();
}

class _PublicationQueueScreenState extends State<PublicationQueueScreen> {
  late Future<List<Opportunity>> _queue;
  final _publishing = <String>{};
  String? _error;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _queue = widget.repository.getAwaitingPublication();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Publication queue'),
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
      body: FutureBuilder<List<Opportunity>>(
        future: _queue,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            final message = snapshot.error is LiveBackendException
                ? (snapshot.error! as LiveBackendException).message
                : 'Could not load the publication queue.';
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
                    OutlinedButton(
                      onPressed: () => setState(_reload),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            );
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final queue = snapshot.data!;
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
                        'Publication queue',
                        style: Theme.of(context).textTheme.headlineLarge,
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Opportunities a verification officer has already '
                        'approved. Publishing makes each one visible to '
                        'applicants.',
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 12),
                        Text(
                          _error!,
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ],
                      const SizedBox(height: 24),
                      if (queue.isEmpty)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 48),
                          child: Center(
                            child: Text('Nothing is waiting to be published.'),
                          ),
                        )
                      else
                        ...queue.map((item) => _row(item)),
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

  Widget _row(Opportunity item) {
    final busy = _publishing.contains(item.id);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        title: Text(item.title),
        subtitle: Text(
          '${item.provider} · deadline '
          '${item.deadline.toLocal().toString().split(' ').first}',
        ),
        trailing: FilledButton.icon(
          onPressed: busy ? null : () => _publish(item),
          icon: busy
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.publish_outlined, size: 18),
          label: Text(busy ? 'Publishing...' : 'Publish'),
        ),
      ),
    );
  }

  Future<void> _publish(Opportunity item) async {
    setState(() {
      _publishing.add(item.id);
      _error = null;
    });
    try {
      await widget.repository.setPublished(item.id, true);
      if (!mounted) return;
      setState(() {
        _publishing.remove(item.id);
        _reload();
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${item.title} is now visible to applicants.')),
      );
    } on LiveBackendException catch (error) {
      if (mounted) {
        setState(() {
          _publishing.remove(item.id);
          _error = error.message;
        });
      }
    }
  }
}
