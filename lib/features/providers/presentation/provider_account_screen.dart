import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../../opportunities/domain/opportunity_repository.dart';
import '../../opportunities/presentation/provider_opportunity_screen.dart';
import '../../provider_analytics/domain/provider_analytics.dart';
import '../data/provider_document_upload.dart';
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
                  ? [_RegistrationForm(user: widget.user, onSubmit: _register)]
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
  const _RegistrationForm({required this.user, required this.onSubmit});
  final UserAccount user;
  final Future<void> Function(Map<String, String>) onSubmit;

  @override
  State<_RegistrationForm> createState() => _RegistrationFormState();
}

class _RegistrationFormState extends State<_RegistrationForm> {
  static const _fieldNames = [
    'name',
    'type',
    'registration',
    'country',
    'website',
    'domain',
    'address',
    'contact',
    'phone',
    'social',
  ];

  // Mirrors the backend's Field(max_length=...) constraints in
  // app/schemas/provider.py so the character count shown here matches what
  // the server will actually accept. Fields without a backend limit (address)
  // are left out on purpose.
  static const _maxLengths = <String, int>{
    'name': 512,
    'type': 128,
    'registration': 255,
    'country': 255,
    'website': 2048,
    'domain': 255,
    'contact': 255,
    'phone': 64,
  };

  static final RegExp _domainPattern = RegExp(
    r'^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
    r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$',
  );

  static bool _isValidDomain(String value) => _domainPattern.hasMatch(value);

  // Forgiving on the way in (dashes, parentheses, spaces all accepted);
  // normalized to a plain digit string (keeping a leading "+" for country
  // codes) once the user leaves the field, so the backend always receives a
  // consistent format regardless of how it was typed.
  static String _normalizePhone(String input) {
    final trimmed = input.trim();
    if (trimmed.isEmpty) return trimmed;
    final hasPlus = trimmed.startsWith('+');
    final digits = trimmed.replaceAll(RegExp(r'[^0-9]'), '');
    if (digits.isEmpty) return trimmed;
    return hasPlus ? '+$digits' : digits;
  }

  final _key = GlobalKey<FormState>();
  late final Map<String, TextEditingController> _fields;
  late final Map<String, FocusNode> _focusNodes;
  final _touched = <String>{};
  final _documentPath = TextEditingController();
  final _upload = ProviderDocumentUpload();
  bool _uploading = false;
  String? _uploadError;

  @override
  void initState() {
    super.initState();
    _fields = {for (final name in _fieldNames) name: TextEditingController()};
    // The organization contact is filling this out while signed in, so we
    // already know their name — no reason to make them retype it.
    _fields['contact']!.text = widget.user.fullName;
    _focusNodes = {for (final name in _fieldNames) name: FocusNode()};
    for (final controller in _fields.values) {
      controller.addListener(() => setState(() {}));
    }
    for (final entry in _focusNodes.entries) {
      entry.value.addListener(() {
        if (entry.value.hasFocus) return;
        setState(() {
          _touched.add(entry.key);
          if (entry.key == 'phone') {
            _fields['phone']!.text = _normalizePhone(_fields['phone']!.text);
          }
        });
      });
    }
  }

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    for (final node in _focusNodes.values) {
      node.dispose();
    }
    _documentPath.dispose();
    super.dispose();
  }

  bool get _requiredFieldsFilled => _fields.entries
      .where((entry) => entry.key != 'social')
      .every((entry) => entry.value.text.trim().isNotEmpty);

  bool get _domainValid => _isValidDomain(_fields['domain']!.text.trim());

  bool get _formValid =>
      _requiredFieldsFilled &&
      _domainValid &&
      _documentPath.text.trim().isNotEmpty;

  String? _errorFor(String key) {
    if (!_touched.contains(key)) return null;
    final value = _fields[key]!.text.trim();
    if (key != 'social' && value.isEmpty) return 'Required';
    if (key == 'domain' && value.isNotEmpty && !_isValidDomain(value)) {
      return 'Enter a valid domain, e.g. university.edu';
    }
    return null;
  }

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
        const SizedBox(height: 4),
        Text(
          'Fields marked * are required.',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade600),
        ),
        const SizedBox(height: 20),
        for (final entry in _fields.entries) ...[
          TextFormField(
            controller: entry.value,
            focusNode: _focusNodes[entry.key],
            maxLength: _maxLengths[entry.key],
            decoration: InputDecoration(
              labelText: entry.key == 'social'
                  ? _label(entry.key)
                  : '${_label(entry.key)} *',
              errorText: _errorFor(entry.key),
              helperText: entry.key == 'phone'
                  ? "Any format works — we'll format it consistently."
                  : null,
              counterText: _maxLengths.containsKey(entry.key)
                  ? '${_maxLengths[entry.key]! - entry.value.text.length} '
                        'characters left'
                  : null,
            ),
            validator: (value) =>
                entry.key != 'social' && (value == null || value.trim().isEmpty)
                ? 'Required'
                : null,
          ),
          const SizedBox(height: 12),
        ],
        _documentField(),
        const SizedBox(height: 20),
        FilledButton.icon(
          onPressed: !_formValid || _uploading ? null : _submit,
          icon: const Icon(Icons.verified_user_outlined),
          label: const Text('Submit for verification'),
        ),
      ],
    ),
  );

  void _submit() {
    if (!_key.currentState!.validate()) return;
    if (_documentPath.text.trim().isEmpty) {
      setState(() => _uploadError = 'Upload a supporting document.');
      return;
    }
    final values = _fields.map(
      (key, value) => MapEntry(
        key,
        key == 'phone'
            ? _normalizePhone(value.text.trim())
            : value.text.trim(),
      ),
    );
    values['document'] = _documentPath.text.trim();
    widget.onSubmit(values);
  }

  Widget _documentField() {
    final uploaded = _documentPath.text.trim().isNotEmpty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Supporting document',
          style: Theme.of(context).textTheme.labelLarge,
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            Icon(
              uploaded ? Icons.check_circle_outline : Icons.upload_file_outlined,
              color: uploaded ? Colors.green : null,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                uploaded
                    ? _documentPath.text.split('/').last
                    : 'No document uploaded yet',
                overflow: TextOverflow.ellipsis,
              ),
            ),
            OutlinedButton(
              onPressed: _uploading ? null : _pickAndUpload,
              child: Text(
                _uploading
                    ? 'Uploading...'
                    : uploaded
                    ? 'Replace'
                    : 'Upload',
              ),
            ),
          ],
        ),
        Text(
          'PDF, JPEG, or PNG, up to 10 MB (e.g. registration certificate).',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        if (_uploadError != null) ...[
          const SizedBox(height: 4),
          Text(
            _uploadError!,
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        ],
      ],
    );
  }

  Future<void> _pickAndUpload() async {
    setState(() {
      _uploading = true;
      _uploadError = null;
    });
    try {
      final path = await _upload.pickAndUpload();
      if (path != null) _documentPath.text = path;
    } on ProviderDocumentUploadFailure catch (error) {
      _uploadError = error.message;
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

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
