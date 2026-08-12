import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../../fraud/domain/fraud_assessment.dart';
import '../../fraud/domain/fraud_detection_service.dart';
import '../../fraud/presentation/fraud_warning_panel.dart';
import '../../opportunities/domain/opportunity.dart';
import '../domain/verification_repository.dart';
import '../domain/verification_review.dart';
import '../../providers/domain/provider_repository.dart';
import '../../providers/presentation/provider_verification_queue_screen.dart';

class VerificationQueueScreen extends StatefulWidget {
  const VerificationQueueScreen({
    super.key,
    required this.user,
    required this.repository,
    required this.providerRepository,
    required this.onSignOut,
  });

  final UserAccount user;
  final VerificationRepository repository;
  final ProviderRepository providerRepository;
  final VoidCallback onSignOut;

  @override
  State<VerificationQueueScreen> createState() =>
      _VerificationQueueScreenState();
}

class _VerificationQueueScreenState extends State<VerificationQueueScreen> {
  late Future<List<Opportunity>> _queue;
  final _fraudDetection = FraudDetectionService();

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _queue = widget.repository.getQueue();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Verification queue'),
        actions: [
          IconButton(
            onPressed: () => Navigator.of(context).push<void>(
              MaterialPageRoute(
                builder: (_) => ProviderVerificationQueueScreen(
                  user: widget.user,
                  repository: widget.providerRepository,
                ),
              ),
            ),
            tooltip: 'Provider verification',
            icon: const Icon(Icons.domain_verification_outlined),
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
                        'Verification queue',
                        style: Theme.of(context).textTheme.headlineLarge,
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Approval requires an authoritative official source '
                        'and every verification check.',
                      ),
                      const SizedBox(height: 24),
                      if (queue.isEmpty)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 48),
                          child: Center(
                            child: Text('The verification queue is clear.'),
                          ),
                        )
                      else
                        ...queue.map((item) {
                          final assessment = _fraudDetection.assess(
                            item,
                            knownOpportunities: queue,
                          );
                          return Card(
                            margin: const EdgeInsets.only(bottom: 12),
                            child: ListTile(
                              contentPadding: const EdgeInsets.all(16),
                              title: Text(item.title),
                              subtitle: Text(
                                '${item.provider} | ${item.verificationLabel}',
                              ),
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  if (assessment.hasWarnings)
                                    Tooltip(
                                      message: assessment.levelLabel,
                                      child: Icon(
                                        Icons.warning_amber_outlined,
                                        color: Theme.of(context)
                                            .colorScheme
                                            .error,
                                      ),
                                    ),
                                  const SizedBox(width: 4),
                                  const Icon(Icons.chevron_right),
                                ],
                              ),
                              onTap: () => _review(item, assessment),
                            ),
                          );
                        }),
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

  Future<void> _review(
    Opportunity opportunity,
    FraudAssessment assessment,
  ) async {
    final latest = await widget.repository.getLatestReview(opportunity.id);
    if (latest == null) {
      await widget.repository.assign(
        opportunityId: opportunity.id,
        officerId: widget.user.id,
        assignedByUserId: widget.user.id,
      );
    }
    if (!mounted) return;
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (context) => VerificationReviewScreen(
          opportunity: opportunity,
          officer: widget.user,
          repository: widget.repository,
          fraudAssessment: assessment,
        ),
      ),
    );
    if (changed == true) setState(_reload);
  }
}

class VerificationReviewScreen extends StatefulWidget {
  const VerificationReviewScreen({
    super.key,
    required this.opportunity,
    required this.officer,
    required this.repository,
    required this.fraudAssessment,
  });

  final Opportunity opportunity;
  final UserAccount officer;
  final VerificationRepository repository;
  final FraudAssessment fraudAssessment;

  @override
  State<VerificationReviewScreen> createState() =>
      _VerificationReviewScreenState();
}

class _VerificationReviewScreenState extends State<VerificationReviewScreen> {
  SourceAuthority _authority = SourceAuthority.officialInstitution;
  VerificationChecklist _checklist = const VerificationChecklist();
  VerificationStatus _decision = VerificationStatus.verified;
  final _notes = TextEditingController();
  final _evidenceLocation = TextEditingController();
  bool _saving = false;
  String? _error;
  String? _awaitingApprovalId;

  @override
  void initState() {
    super.initState();
    _loadLatest();
  }

  Future<void> _loadLatest() async {
    final latest = await widget.repository.getLatestReview(
      widget.opportunity.id,
    );
    if (latest?.workflowStatus ==
            VerificationWorkflowStatus.awaitingSecondApproval &&
        mounted) {
      setState(() => _awaitingApprovalId = latest!.verificationId);
    }
  }

  @override
  void dispose() {
    _notes.dispose();
    _evidenceLocation.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Verify opportunity')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.opportunity.title,
                    style: Theme.of(context).textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(widget.opportunity.provider),
                  const SizedBox(height: 20),
                  FraudWarningPanel(assessment: widget.fraudAssessment),
                  const SizedBox(height: 20),
                  _sourceEvidence(context),
                  const SizedBox(height: 24),
                  Text(
                    'Verification checklist',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  _check(
                    'Organization exists',
                    _checklist.organizationExists,
                    (value) => _checklist = _checklist.copyWith(
                      organizationExists: value,
                    ),
                  ),
                  _check(
                    'Official website checked',
                    _checklist.officialWebsiteChecked,
                    (value) => _checklist = _checklist.copyWith(
                      officialWebsiteChecked: value,
                    ),
                  ),
                  _check(
                    'Sponsor or institution confirmed',
                    _checklist.sponsorConfirmed,
                    (value) => _checklist = _checklist.copyWith(
                      sponsorConfirmed: value,
                    ),
                  ),
                  _check(
                    'Application is currently open',
                    _checklist.applicationOpen,
                    (value) => _checklist = _checklist.copyWith(
                      applicationOpen: value,
                    ),
                  ),
                  _check(
                    'Application link tested',
                    _checklist.applicationLinkTested,
                    (value) => _checklist = _checklist.copyWith(
                      applicationLinkTested: value,
                    ),
                  ),
                  _check(
                    'Deadline confirmed',
                    _checklist.deadlineConfirmed,
                    (value) => _checklist = _checklist.copyWith(
                      deadlineConfirmed: value,
                    ),
                  ),
                  _check(
                    'Requirements reviewed',
                    _checklist.requirementsReviewed,
                    (value) => _checklist = _checklist.copyWith(
                      requirementsReviewed: value,
                    ),
                  ),
                  _check(
                    'Funding details confirmed',
                    _checklist.fundingConfirmed,
                    (value) => _checklist = _checklist.copyWith(
                      fundingConfirmed: value,
                    ),
                  ),
                  _check(
                    'Application fees confirmed',
                    _checklist.feesConfirmed,
                    (value) =>
                        _checklist = _checklist.copyWith(feesConfirmed: value),
                  ),
                  _check(
                    'Contact details confirmed',
                    _checklist.contactDetailsConfirmed,
                    (value) => _checklist = _checklist.copyWith(
                      contactDetailsConfirmed: value,
                    ),
                  ),
                  _check(
                    'No misleading claims',
                    _checklist.noMisleadingClaims,
                    (value) => _checklist = _checklist.copyWith(
                      noMisleadingClaims: value,
                    ),
                  ),
                  _check(
                    'Duplicate listings checked',
                    _checklist.duplicatesChecked,
                    (value) => _checklist = _checklist.copyWith(
                      duplicatesChecked: value,
                    ),
                  ),
                  _check(
                    'Supporting evidence stored',
                    _checklist.supportingEvidenceStored,
                    (value) => _checklist = _checklist.copyWith(
                      supportingEvidenceStored: value,
                    ),
                  ),
                  const SizedBox(height: 20),
                  DropdownButtonFormField<VerificationStatus>(
                    initialValue: _decision,
                    decoration: const InputDecoration(
                      labelText: 'Review decision',
                    ),
                    items:
                        const [
                              VerificationStatus.verified,
                              VerificationStatus.incomplete,
                              VerificationStatus.suspicious,
                              VerificationStatus.rejected,
                              VerificationStatus.expired,
                              VerificationStatus.archived,
                            ]
                            .map(
                              (status) => DropdownMenuItem(
                                value: status,
                                child: Text(_statusLabel(status)),
                              ),
                            )
                            .toList(),
                    onChanged: (value) => setState(
                      () => _decision = value ?? VerificationStatus.incomplete,
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _evidenceLocation,
                    decoration: const InputDecoration(
                      labelText: 'Evidence attachment or storage location',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _notes,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      labelText: 'Evidence and review notes',
                    ),
                  ),
                  if (_decision == VerificationStatus.verified) ...[
                    const SizedBox(height: 12),
                    const Text(
                      'Next verification will be scheduled in 90 days.',
                    ),
                  ],
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      _error!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                  const SizedBox(height: 28),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: _saving ? null : _save,
                      icon: const Icon(Icons.fact_check_outlined),
                      label: Text(
                        _saving
                            ? 'Saving review...'
                            : _awaitingApprovalId != null
                            ? 'Second-level approval'
                            : 'Submit for second approval',
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sourceEvidence(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Source authority',
        style: Theme.of(context).textTheme.headlineSmall,
      ),
      const SizedBox(height: 8),
      SelectableText(widget.opportunity.officialSourceUrl),
      const SizedBox(height: 12),
      DropdownButtonFormField<SourceAuthority>(
        initialValue: _authority,
        decoration: const InputDecoration(labelText: 'Source type'),
        items: SourceAuthority.values
            .map(
              (authority) => DropdownMenuItem(
                value: authority,
                child: Text(_sourceLabel(authority)),
              ),
            )
            .toList(),
        onChanged: (value) => setState(
          () => _authority = value ?? SourceAuthority.unverifiedThirdParty,
        ),
      ),
    ],
  );

  Widget _check(String label, bool value, ValueChanged<bool> update) =>
      CheckboxListTile(
        contentPadding: EdgeInsets.zero,
        value: value,
        title: Text(label),
        controlAffinity: ListTileControlAffinity.leading,
        onChanged: (checked) => setState(() => update(checked ?? false)),
      );

  Future<void> _save() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    final now = DateTime.now();
    try {
      final awaitingId = _awaitingApprovalId;
      if (awaitingId != null) {
        await widget.repository.approveSecondLevel(
          verificationId: awaitingId,
          approverId: widget.officer.id,
        );
      } else {
        final review = VerificationReview(
          verificationId: 'verification-${now.microsecondsSinceEpoch}',
          opportunityId: widget.opportunity.id,
          assignedToUserId: widget.officer.id,
          sourceAuthority: _authority,
          checklist: _checklist,
          status: _decision == VerificationStatus.verified
              ? VerificationStatus.pending
              : _decision,
          workflowStatus: _workflowStatus(_decision),
          officialSourceUrl: widget.opportunity.officialSourceUrl,
          evidenceLocation: _evidenceLocation.text.trim(),
          notes: _notes.text.trim(),
          reviewedByUserId: widget.officer.id,
          reviewedAt: now,
          expiresAt: now.add(const Duration(days: 90)),
          nextReviewAt: now.add(const Duration(days: 90)),
        );
        if (_decision == VerificationStatus.verified) {
          await widget.repository.submitForSecondApproval(review);
        } else {
          await widget.repository.submitReview(review);
        }
      }
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on VerificationFailure catch (failure) {
      if (mounted) setState(() => _error = failure.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  static String _sourceLabel(SourceAuthority value) => switch (value) {
    SourceAuthority.officialInstitution => 'Official institution',
    SourceAuthority.government => 'Government portal',
    SourceAuthority.embassy => 'Embassy',
    SourceAuthority.officialSponsor => 'Official sponsor',
    SourceAuthority.internationalOrganization => 'International organization',
    SourceAuthority.unverifiedThirdParty => 'Unverified third party',
  };

  static String _statusLabel(VerificationStatus value) => switch (value) {
    VerificationStatus.verified => 'Verified',
    VerificationStatus.incomplete => 'Information incomplete',
    VerificationStatus.suspicious => 'Suspicious',
    VerificationStatus.rejected => 'Rejected',
    VerificationStatus.expired => 'Expired',
    VerificationStatus.archived => 'Archived',
    VerificationStatus.pending => 'Pending verification',
    VerificationStatus.verificationExpired => 'Verification expired',
  };

  static VerificationWorkflowStatus _workflowStatus(VerificationStatus value) =>
      switch (value) {
        VerificationStatus.verified =>
          VerificationWorkflowStatus.awaitingSecondApproval,
        VerificationStatus.incomplete =>
          VerificationWorkflowStatus.additionalEvidenceRequired,
        VerificationStatus.suspicious => VerificationWorkflowStatus.suspicious,
        VerificationStatus.rejected => VerificationWorkflowStatus.rejected,
        VerificationStatus.archived => VerificationWorkflowStatus.archived,
        VerificationStatus.expired || VerificationStatus.verificationExpired =>
          VerificationWorkflowStatus.verificationExpired,
        VerificationStatus.pending => VerificationWorkflowStatus.underReview,
      };
}
