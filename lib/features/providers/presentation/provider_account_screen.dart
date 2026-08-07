import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../../opportunities/domain/opportunity_repository.dart';
import '../../opportunities/presentation/provider_opportunity_screen.dart';
import '../../provider_analytics/domain/provider_analytics.dart';
import '../domain/provider_profile.dart';
import '../domain/provider_repository.dart';

class ProviderAccountScreen extends StatefulWidget {
  const ProviderAccountScreen({
    super.key,
    required this.user,
    required this.providerRepository,
    required this.opportunityRepository,
    required this.analyticsRepository,
    required this.onSignOut,
  });

  final UserAccount user;
  final ProviderRepository providerRepository;
  final OpportunityRepository opportunityRepository;
  final ProviderAnalyticsRepository analyticsRepository;
  final VoidCallback onSignOut;

  @override
  State<ProviderAccountScreen> createState() => _ProviderAccountScreenState();
}

class _ProviderAccountScreenState extends State<ProviderAccountScreen> {
  late Future<ProviderProfile?> _profile;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() =>
      _profile = widget.providerRepository.getForUser(widget.user.id);

  @override
  Widget build(BuildContext context) => FutureBuilder<ProviderProfile?>(
    future: _profile,
    builder: (context, snapshot) {
      if (!snapshot.hasData &&
          snapshot.connectionState != ConnectionState.done) {
        return const Scaffold(body: Center(child: CircularProgressIndicator()));
      }
      final profile = snapshot.data;
      if (profile?.hasVerifiedBadge == true) {
        return ProviderOpportunityScreen(
          user: widget.user,
          repository: widget.opportunityRepository,
          analyticsRepository: widget.analyticsRepository,
          onSignOut: widget.onSignOut,
        );
      }
      return Scaffold(
        appBar: AppBar(
          title: const Text('Provider verification'),
          actions: [
            IconButton(
              onPressed: widget.onSignOut,
              tooltip: 'Sign out',
              icon: const Icon(Icons.logout),
            ),
          ],
        ),
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: profile == null
                  ? [_RegistrationForm(onSubmit: _register)]
                  : [_StatusPanel(profile: profile, onAppeal: _appeal)],
            ),
          ),
        ),
      );
    },
  );

  Future<void> _register(Map<String, String> values) async {
    final now = DateTime.now();
    await widget.providerRepository.register(
      ProviderProfile(
        id: 'provider-${now.microsecondsSinceEpoch}',
        ownerUserId: widget.user.id,
        organizationName: values['name']!,
        organizationType: values['type']!,
        registrationNumber: values['registration']!,
        country: values['country']!,
        officialWebsite: values['website']!,
        officialEmailDomain: values['domain']!,
        physicalAddress: values['address']!,
        contactPerson: values['contact']!,
        contactPhone: values['phone']!,
        supportingDocuments: [values['document']!],
        socialMediaLinks: values['social']!.isEmpty
            ? const []
            : [values['social']!],
        status: ProviderStatus.draft,
        riskScore: 0,
        permissions: const {},
      ),
    );
    if (mounted) setState(_reload);
  }

  Future<void> _appeal(ProviderProfile profile) async {
    await widget.providerRepository.appeal(
      profile.id,
      'Organization requests a manual review of the decision.',
    );
    if (mounted) setState(_reload);
  }
}

class _RegistrationForm extends StatefulWidget {
  const _RegistrationForm({required this.onSubmit});
  final Future<void> Function(Map<String, String>) onSubmit;

  @override
  State<_RegistrationForm> createState() => _RegistrationFormState();
}

class _RegistrationFormState extends State<_RegistrationForm> {
  final _key = GlobalKey<FormState>();
  final _fields = <String, TextEditingController>{
    for (final name in [
      'name',
      'type',
      'registration',
      'country',
      'website',
      'domain',
      'address',
      'contact',
      'phone',
      'document',
      'social',
    ])
      name: TextEditingController(),
  };

  @override
  Widget build(BuildContext context) => Form(
    key: _key,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Register your organization',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 20),
        for (final entry in _fields.entries) ...[
          TextFormField(
            controller: entry.value,
            decoration: InputDecoration(labelText: _label(entry.key)),
            validator: (value) =>
                entry.key != 'social' && (value == null || value.trim().isEmpty)
                ? 'Required'
                : null,
          ),
          const SizedBox(height: 12),
        ],
        FilledButton.icon(
          onPressed: () {
            if (!_key.currentState!.validate()) return;
            widget.onSubmit(
              _fields.map((key, value) => MapEntry(key, value.text.trim())),
            );
          },
          icon: const Icon(Icons.verified_user_outlined),
          label: const Text('Submit for verification'),
        ),
      ],
    ),
  );

  String _label(String key) => {
    'name': 'Organization name',
    'type': 'Organization type',
    'registration': 'Registration number',
    'country': 'Country',
    'website': 'Official website',
    'domain': 'Official email domain',
    'address': 'Physical address',
    'contact': 'Contact person',
    'phone': 'Contact phone number',
    'document': 'Supporting document reference',
    'social': 'Social media link (optional)',
  }[key]!;
}

class _StatusPanel extends StatelessWidget {
  const _StatusPanel({required this.profile, required this.onAppeal});
  final ProviderProfile profile;
  final Future<void> Function(ProviderProfile) onAppeal;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        profile.organizationName,
        style: Theme.of(context).textTheme.headlineLarge,
      ),
      const SizedBox(height: 12),
      Chip(label: Text(profile.status.name)),
      const SizedBox(height: 12),
      Text(
        'Risk assessment: ${profile.riskLevel.name} (${profile.riskScore}/100)',
      ),
      if (profile.reviewNote != null) ...[
        const SizedBox(height: 12),
        Text(profile.reviewNote!),
      ],
      if ({
        ProviderStatus.rejected,
        ProviderStatus.suspended,
      }.contains(profile.status)) ...[
        const SizedBox(height: 20),
        OutlinedButton.icon(
          onPressed: () => onAppeal(profile),
          icon: const Icon(Icons.rate_review_outlined),
          label: const Text('Submit appeal'),
        ),
      ],
    ],
  );
}
