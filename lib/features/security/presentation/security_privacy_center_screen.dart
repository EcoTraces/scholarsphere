import 'package:flutter/material.dart';

import '../../applications/domain/application_repository.dart';
import '../../authentication/domain/user_account.dart';
import '../../documents/domain/document_repository.dart';
import '../../privacy/domain/privacy_data_export_service.dart';
import '../../privacy/domain/privacy_models.dart';
import '../../privacy/domain/privacy_repository.dart';
import '../../privacy/domain/privacy_rules.dart';
import '../../profiles/domain/applicant_profile.dart';
import '../../profiles/domain/applicant_profile_repository.dart';
import '../domain/security_models.dart';
import '../domain/security_repository.dart';

class SecurityPrivacyCenterScreen extends StatelessWidget {
  const SecurityPrivacyCenterScreen({
    super.key,
    required this.user,
    required this.securityRepository,
    required this.privacyRepository,
    required this.profileRepository,
    required this.applicationRepository,
    required this.documentRepository,
  });

  final UserAccount user;
  final SecurityRepository securityRepository;
  final PrivacyRepository privacyRepository;
  final ApplicantProfileRepository profileRepository;
  final ApplicationRepository applicationRepository;
  final DocumentRepository documentRepository;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Security and privacy'),
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.security_outlined), text: 'Security'),
              Tab(icon: Icon(Icons.privacy_tip_outlined), text: 'Privacy'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _SecurityView(user: user, repository: securityRepository),
            _PrivacyView(
              user: user,
              repository: privacyRepository,
              profileRepository: profileRepository,
              exportService: PrivacyDataExportService(
                profileRepository: profileRepository,
                applicationRepository: applicationRepository,
                documentRepository: documentRepository,
                privacyRepository: privacyRepository,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SecurityView extends StatefulWidget {
  const _SecurityView({required this.user, required this.repository});

  final UserAccount user;
  final SecurityRepository repository;

  @override
  State<_SecurityView> createState() => _SecurityViewState();
}

class _SecurityViewState extends State<_SecurityView> {
  late Future<
    ({
      List<SecuritySession> sessions,
      List<LoginHistoryEntry> history,
      List<SecurityAlert> alerts,
    })
  >
  _data;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _data = _load();
  }

  Future<
    ({
      List<SecuritySession> sessions,
      List<LoginHistoryEntry> history,
      List<SecurityAlert> alerts,
    })
  >
  _load() async => (
    sessions: await widget.repository.getSessions(widget.user.id),
    history: await widget.repository.getLoginHistory(widget.user.email),
    alerts: await widget.repository.getAlerts(widget.user.id),
  );

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<
      ({
        List<SecuritySession> sessions,
        List<LoginHistoryEntry> history,
        List<SecurityAlert> alerts,
      })
    >(
      future: _data,
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
                constraints: const BoxConstraints(maxWidth: 820),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _statusPanel(context),
                    const SizedBox(height: 24),
                    _heading(context, 'Sessions and devices'),
                    for (final session in data.sessions)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.devices_outlined),
                        title: Text(
                          '${session.device.browser} on '
                          '${session.device.operatingSystem}',
                        ),
                        subtitle: Text(
                          '${session.device.ipAddress} | Expires '
                          '${_dateTime(session.expiresAt)}'
                          '${session.revokedAt == null ? '' : ' | Revoked'}',
                        ),
                        trailing: session.revokedAt == null
                            ? IconButton(
                                tooltip: 'Revoke session',
                                onPressed: () async {
                                  await widget.repository.revokeSession(
                                    session.id,
                                  );
                                  if (mounted) setState(_reload);
                                },
                                icon: const Icon(Icons.logout),
                              )
                            : null,
                      ),
                    const SizedBox(height: 20),
                    _heading(context, 'Security alerts'),
                    if (data.alerts.isEmpty)
                      const Text('No security alerts.')
                    else
                      for (final alert in data.alerts)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.warning_amber_outlined),
                          title: Text(_label(alert.type.name)),
                          subtitle: Text(alert.message),
                        ),
                    const SizedBox(height: 20),
                    _heading(context, 'Login history'),
                    for (final entry in data.history)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(
                          entry.outcome == LoginOutcome.success
                              ? Icons.check_circle_outline
                              : Icons.error_outline,
                        ),
                        title: Text(_label(entry.outcome.name)),
                        subtitle: Text(
                          '${entry.device.browser} | '
                          '${entry.device.ipAddress} | '
                          '${_dateTime(entry.occurredAt)}',
                        ),
                        trailing: entry.suspicious
                            ? const Tooltip(
                                message: 'Suspicious login',
                                child: Icon(Icons.gpp_maybe_outlined),
                              )
                            : null,
                      ),
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _statusPanel(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.primaryContainer,
      borderRadius: BorderRadius.circular(8),
    ),
    child: Row(
      children: [
        const Icon(Icons.verified_user_outlined),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            widget.user.twoFactorEnabled
                ? 'Multi-factor authentication is enabled.'
                : 'Multi-factor authentication is not enabled.',
          ),
        ),
      ],
    ),
  );

  Widget _heading(BuildContext context, String value) =>
      Text(value, style: Theme.of(context).textTheme.headlineSmall);
}

class _PrivacyView extends StatefulWidget {
  const _PrivacyView({
    required this.user,
    required this.repository,
    required this.profileRepository,
    required this.exportService,
  });

  final UserAccount user;
  final PrivacyRepository repository;
  final ApplicantProfileRepository profileRepository;
  final PrivacyDataExportService exportService;

  @override
  State<_PrivacyView> createState() => _PrivacyViewState();
}

class _PrivacyViewState extends State<_PrivacyView> {
  late Future<
    ({
      List<ConsentRecord> consents,
      List<PrivacyRequest> requests,
      List<OrganizationAccessRecord> access,
      ApplicantProfile? profile,
    })
  >
  _data;
  String? _message;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _data = _load();
  }

  Future<
    ({
      List<ConsentRecord> consents,
      List<PrivacyRequest> requests,
      List<OrganizationAccessRecord> access,
      ApplicantProfile? profile,
    })
  >
  _load() async {
    final profile = await widget.profileRepository.getForUser(widget.user.id);
    await widget.repository.setMinorStatus(
      widget.user.id,
      PrivacyRules.isMinor(profile?.dateOfBirth, DateTime.now()),
    );
    return (
      consents: await widget.repository.getConsents(widget.user.id),
      requests: await widget.repository.getRequests(widget.user.id),
      access: await widget.repository.getAccessHistory(widget.user.id),
      profile: profile,
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<
      ({
        List<ConsentRecord> consents,
        List<PrivacyRequest> requests,
        List<OrganizationAccessRecord> access,
        ApplicantProfile? profile,
      })
    >(
      future: _data,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final data = snapshot.data!;
        final active = {
          for (final consent in data.consents)
            if (consent.isActive) consent.type,
        };
        final minor = PrivacyRules.isMinor(
          data.profile?.dateOfBirth,
          DateTime.now(),
        );
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 820),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Stored personal information',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text('Name: ${widget.user.fullName}'),
                    Text('Email: ${widget.user.email}'),
                    Text(
                      'Nationality: '
                      '${data.profile?.nationality.isNotEmpty == true ? data.profile!.nationality : 'Not provided'}',
                    ),
                    Text(
                      'Country of residence: '
                      '${data.profile?.countryOfResidence.isNotEmpty == true ? data.profile!.countryOfResidence : 'Not provided'}',
                    ),
                    if (minor) ...[
                      const SizedBox(height: 10),
                      const Text(
                        'Minor-account restrictions are active. Marketing, '
                        'behavioural personalization, and third-party sharing '
                        'cannot be enabled.',
                      ),
                    ],
                    const SizedBox(height: 24),
                    Text(
                      'Consent preferences',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    for (final type in ConsentType.values)
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(_consentLabel(type)),
                        subtitle:
                            {
                              ConsentType.privacyPolicy,
                              ConsentType.termsAndConditions,
                            }.contains(type)
                            ? const Text('Required while the account is active')
                            : null,
                        value: active.contains(type),
                        onChanged: minor && !PrivacyRules.minorCanGrant(type)
                            ? null
                            : (enabled) => _setConsent(type, enabled),
                      ),
                    if (_message != null)
                      Text(
                        _message!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    const SizedBox(height: 24),
                    Text(
                      'Your privacy rights',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        OutlinedButton.icon(
                          onPressed: _export,
                          icon: const Icon(Icons.download_outlined),
                          label: const Text('Download my data'),
                        ),
                        OutlinedButton.icon(
                          onPressed: () =>
                              _request(PrivacyRequestType.dataCorrection),
                          icon: const Icon(Icons.edit_outlined),
                          label: const Text('Request correction'),
                        ),
                        OutlinedButton.icon(
                          onPressed: () =>
                              _request(PrivacyRequestType.documentDeletion),
                          icon: const Icon(Icons.delete_outline),
                          label: const Text('Delete documents'),
                        ),
                        FilledButton.tonalIcon(
                          onPressed: () =>
                              _request(PrivacyRequestType.accountDeletion),
                          icon: const Icon(Icons.person_remove_outlined),
                          label: const Text('Delete account'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    Text(
                      'Organizations that accessed your information',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    if (data.access.isEmpty)
                      const Text('No organization access has been recorded.')
                    else
                      for (final record in data.access)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.business_outlined),
                          title: Text(record.organizationName),
                          subtitle: Text(record.dataCategories.join(', ')),
                        ),
                    const SizedBox(height: 24),
                    Text(
                      'Privacy requests',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    if (data.requests.isEmpty)
                      const Text('No privacy requests submitted.')
                    else
                      for (final request in data.requests)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(_label(request.type.name)),
                          subtitle: Text(_label(request.status.name)),
                        ),
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _setConsent(ConsentType type, bool enabled) async {
    try {
      if (enabled) {
        await widget.repository.grantConsent(
          userId: widget.user.id,
          type: type,
          policyVersion: '2026-07',
        );
      } else {
        await widget.repository.withdrawConsent(widget.user.id, type);
      }
      if (mounted) {
        setState(() {
          _message = null;
          _reload();
        });
      }
    } on PrivacyFailure catch (failure) {
      if (mounted) setState(() => _message = failure.message);
    }
  }

  Future<void> _request(PrivacyRequestType type) async {
    await widget.repository.submitRequest(userId: widget.user.id, type: type);
    if (mounted) setState(_reload);
  }

  Future<void> _export() async {
    await widget.repository.submitRequest(
      userId: widget.user.id,
      type: PrivacyRequestType.dataExport,
    );
    final json = await widget.exportService.export(widget.user);
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Your ScholarSphere data'),
        content: SizedBox(
          width: 640,
          child: SingleChildScrollView(child: SelectableText(json)),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
    if (mounted) setState(_reload);
  }
}

String _dateTime(DateTime value) =>
    '${value.day}/${value.month}/${value.year} '
    '${value.hour.toString().padLeft(2, '0')}:'
    '${value.minute.toString().padLeft(2, '0')}';

String _label(String value) {
  final spaced = value.replaceAllMapped(
    RegExp(r'([A-Z])'),
    (match) => ' ${match.group(1)!.toLowerCase()}',
  );
  return spaced.isEmpty
      ? value
      : '${spaced[0].toUpperCase()}${spaced.substring(1)}';
}

String _consentLabel(ConsentType type) => switch (type) {
  ConsentType.privacyPolicy => 'Privacy policy',
  ConsentType.termsAndConditions => 'Terms and conditions',
  ConsentType.cookies => 'Cookies',
  ConsentType.marketing => 'Promotional communication',
  ConsentType.notifications => 'Notifications',
  ConsentType.personalizedRecommendations => 'Behavioural recommendations',
  ConsentType.sensitiveData => 'Sensitive profile data',
  ConsentType.documentStorage => 'Document storage',
  ConsentType.thirdPartySharing => 'Third-party data sharing',
};
