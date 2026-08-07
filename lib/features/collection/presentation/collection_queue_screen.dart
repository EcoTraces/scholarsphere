import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../../opportunities/domain/opportunity.dart';
import '../domain/collected_opportunity.dart';
import '../domain/opportunity_collection_repository.dart';

class CollectionQueueScreen extends StatefulWidget {
  const CollectionQueueScreen({
    super.key,
    required this.user,
    required this.repository,
    required this.onSignOut,
  });

  final UserAccount user;
  final OpportunityCollectionRepository repository;
  final VoidCallback onSignOut;

  @override
  State<CollectionQueueScreen> createState() => _CollectionQueueScreenState();
}

class _CollectionQueueScreenState extends State<CollectionQueueScreen> {
  late Future<List<CollectedOpportunity>> _records;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _records = widget.repository.getIntakeLedger();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Opportunity collection'),
        actions: [
          IconButton(
            onPressed: widget.onSignOut,
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: FutureBuilder<List<CollectedOpportunity>>(
        future: _records,
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final records = snapshot.data!;
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
                        'Collection intake ledger',
                        style: Theme.of(context).textTheme.headlineLarge,
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Collected records never publish automatically. Every '
                        'record is sent to the verification queue.',
                      ),
                      const SizedBox(height: 20),
                      FilledButton.icon(
                        onPressed: _openIntake,
                        icon: const Icon(Icons.add_link),
                        label: const Text('Collect source'),
                      ),
                      const SizedBox(height: 24),
                      if (records.isEmpty)
                        const Center(child: Text('No sources collected yet.'))
                      else
                        ...records.map(
                          (record) => Card(
                            margin: const EdgeInsets.only(bottom: 12),
                            child: ListTile(
                              contentPadding: const EdgeInsets.all(16),
                              title: Text(_sourceLabel(record.sourceType)),
                              subtitle: Text(record.sourceLocation),
                              trailing: const Chip(
                                label: Text('Pending verification'),
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
        },
      ),
    );
  }

  Future<void> _openIntake() async {
    final created = await showDialog<bool>(
      context: context,
      builder: (context) => _CollectionDialog(
        userId: widget.user.id,
        repository: widget.repository,
      ),
    );
    if (created == true) setState(_reload);
  }

  static String _sourceLabel(CollectionSourceType type) => switch (type) {
    CollectionSourceType.manualAdministrator => 'Manual administrator entry',
    CollectionSourceType.providerSubmission => 'Provider submission',
    CollectionSourceType.officialApi => 'Official API',
    CollectionSourceType.approvedRss => 'Approved RSS feed',
    CollectionSourceType.structuredFeed => 'Structured data feed',
    CollectionSourceType.controlledWebCollection => 'Controlled web collection',
    CollectionSourceType.userSubmission => 'User submission',
  };
}

class _CollectionDialog extends StatefulWidget {
  const _CollectionDialog({required this.userId, required this.repository});

  final String userId;
  final OpportunityCollectionRepository repository;

  @override
  State<_CollectionDialog> createState() => _CollectionDialogState();
}

class _CollectionDialogState extends State<_CollectionDialog> {
  final _source = TextEditingController();
  CollectionSourceType _type = CollectionSourceType.manualAdministrator;
  bool _approved = true;
  String? _error;

  @override
  void dispose() {
    _source.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Collect opportunity source'),
      content: SizedBox(
        width: 520,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<CollectionSourceType>(
              initialValue: _type,
              decoration: const InputDecoration(labelText: 'Source type'),
              items: CollectionSourceType.values
                  .map(
                    (type) =>
                        DropdownMenuItem(value: type, child: Text(type.name)),
                  )
                  .toList(),
              onChanged: (value) => setState(() => _type = value ?? _type),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _source,
              decoration: const InputDecoration(
                labelText: 'Official source URL or feed identifier',
              ),
            ),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              value: _approved,
              title: const Text('Approved source'),
              onChanged: (value) => setState(() => _approved = value ?? false),
            ),
            if (_error != null)
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _collect,
          child: const Text('Add to verification queue'),
        ),
      ],
    );
  }

  Future<void> _collect() async {
    final source = _source.text.trim();
    if (source.isEmpty) {
      setState(() => _error = 'Enter source provenance.');
      return;
    }
    try {
      await widget.repository.collect(
        opportunity: _draft(source),
        sourceType: _type,
        sourceLocation: source,
        automated: {
          CollectionSourceType.officialApi,
          CollectionSourceType.approvedRss,
          CollectionSourceType.structuredFeed,
          CollectionSourceType.controlledWebCollection,
        }.contains(_type),
        approvedSource: _approved,
        collectedByUserId: widget.userId,
      );
      if (mounted) Navigator.of(context).pop(true);
    } on CollectionFailure catch (failure) {
      if (mounted) setState(() => _error = failure.message);
    }
  }

  Opportunity _draft(String source) => Opportunity(
    id: 'collected-${DateTime.now().microsecondsSinceEpoch}',
    title: 'Collected opportunity awaiting review',
    provider: 'Unconfirmed sponsor',
    hostInstitution: 'Unconfirmed institution',
    hostCountry: 'Global',
    type: OpportunityType.scholarship,
    funding: FundingType.partiallyFunded,
    deadline: DateTime.now().add(const Duration(days: 90)),
    applicationOpenDate: DateTime.now(),
    verificationStatus: VerificationStatus.pending,
    lastVerifiedAt: null,
    officialSourceUrl: source,
    applicationUrl: source,
    eligibleNationalities: const ['To be verified'],
    studyLevels: const ['To be verified'],
    fieldsOfStudy: const ['To be verified'],
    summary: 'Collected source awaiting verification and enrichment.',
    benefits: const ['To be verified'],
    eligibilityRequirements: const ['To be verified'],
    requiredDocuments: const [],
    applicationProcedure: const ['To be verified'],
    languageRequirements: const [],
    minimumAge: null,
    maximumAge: null,
    workExperienceYearsRequired: null,
    contactInformation: 'To be verified',
    availablePositions: null,
    deliveryFormat: DeliveryFormat.online,
  );
}
