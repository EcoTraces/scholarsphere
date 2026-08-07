import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../domain/provider_profile.dart';
import '../domain/provider_repository.dart';

class ProviderVerificationQueueScreen extends StatefulWidget {
  const ProviderVerificationQueueScreen({
    super.key,
    required this.user,
    required this.repository,
  });
  final UserAccount user;
  final ProviderRepository repository;

  @override
  State<ProviderVerificationQueueScreen> createState() =>
      _ProviderVerificationQueueScreenState();
}

class _ProviderVerificationQueueScreenState
    extends State<ProviderVerificationQueueScreen> {
  late Future<List<ProviderProfile>> _queue;
  void _reload() => _queue = widget.repository.getReviewQueue();

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Provider verification')),
    body: FutureBuilder<List<ProviderProfile>>(
      future: _queue,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        return ListView(
          padding: const EdgeInsets.all(24),
          children: snapshot.data!
              .map(
                (provider) => Card(
                  child: ListTile(
                    title: Text(provider.organizationName),
                    subtitle: Text(
                      '${provider.officialEmailDomain} | Risk ${provider.riskScore}/100',
                    ),
                    trailing: FilledButton(
                      onPressed: () => _review(provider),
                      child: const Text('Review'),
                    ),
                  ),
                ),
              )
              .toList(),
        );
      },
    ),
  );

  Future<void> _review(ProviderProfile provider) async {
    var complete = false;
    final approved = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(provider.organizationName),
          content: CheckboxListTile(
            value: complete,
            onChanged: (value) =>
                setDialogState(() => complete = value ?? false),
            title: const Text(
              'All email, domain, contact, document and impersonation checks passed',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Request information'),
            ),
            FilledButton(
              onPressed: complete ? () => Navigator.pop(context, true) : null,
              child: const Text('Verify provider'),
            ),
          ],
        ),
      ),
    );
    if (approved == null) return;
    await widget.repository.review(
      providerId: provider.id,
      officerId: widget.user.id,
      decision: approved
          ? ProviderStatus.verified
          : ProviderStatus.additionalInformationRequired,
      checklist: ProviderReviewChecklist(
        officialEmailVerified: complete,
        domainVerified: complete,
        contactVerified: complete,
        documentsVerified: complete,
        impersonationCheckPassed: complete,
      ),
    );
    if (mounted) setState(_reload);
  }
}
