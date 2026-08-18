import 'package:flutter/material.dart';

import '../../applications/domain/application_repository.dart';
import '../../documents/domain/document_repository.dart';
import '../../documents/presentation/document_readiness_panel.dart';
import '../../fraud/domain/fraud_assessment.dart';
import '../../fraud/presentation/fraud_warning_panel.dart';
import '../../matching/domain/eligibility_matcher.dart';
import '../../matching/presentation/eligibility_match_panel.dart';
import '../../guidance/domain/application_guidance_repository.dart';
import '../../guidance/presentation/application_guidance_screen.dart';
import '../../governance/domain/legal_compliance.dart';
import '../../moderation/domain/moderation_case.dart';
import '../../moderation/domain/moderation_repository.dart';
import '../../moderation/presentation/report_content_screen.dart';
import '../../profiles/domain/applicant_profile.dart';
import '../domain/opportunity.dart';

class OpportunityDetailScreen extends StatelessWidget {
  const OpportunityDetailScreen({
    super.key,
    required this.opportunity,
    required this.profile,
    required this.userId,
    required this.applicationRepository,
    required this.documentRepository,
    required this.fraudAssessment,
    required this.moderationRepository,
    required this.guidanceRepository,
  });

  final Opportunity opportunity;
  final ApplicantProfile profile;
  final String userId;
  final ApplicationRepository applicationRepository;
  final DocumentRepository documentRepository;
  final FraudAssessment fraudAssessment;
  final ModerationRepository moderationRepository;
  final ApplicationGuidanceRepository guidanceRepository;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Opportunity details'),
        actions: [
          IconButton(
            tooltip: 'Application guidance',
            icon: const Icon(Icons.checklist),
            onPressed: () async {
              final documents = await documentRepository.getForUser(userId);
              if (!context.mounted) return;
              await Navigator.of(context).push<void>(
                MaterialPageRoute(
                  builder: (_) => ApplicationGuidanceScreen(
                    userId: userId,
                    opportunity: opportunity,
                    profile: profile,
                    documents: documents,
                    repository: guidanceRepository,
                  ),
                ),
              );
            },
          ),
          IconButton(
            tooltip: 'Report opportunity',
            icon: const Icon(Icons.flag_outlined),
            onPressed: () => Navigator.of(context).push<void>(
              MaterialPageRoute(
                builder: (_) => ReportContentScreen(
                  reporterId: userId,
                  entityType: ReportedEntityType.opportunity,
                  entityId: opportunity.id,
                  repository: moderationRepository,
                ),
              ),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (opportunity.isVerified)
                    Chip(
                      avatar: const Icon(Icons.verified_outlined, size: 18),
                      label: Text(_verificationText(opportunity)),
                    ),
                  const SizedBox(height: 12),
                  FraudWarningPanel(assessment: fraudAssessment),
                  const SizedBox(height: 12),
                  const Text(RequiredLegalDisclaimers.noGuarantee),
                  const SizedBox(height: 4),
                  const Text(RequiredLegalDisclaimers.officialSource),
                  const SizedBox(height: 4),
                  const Text(RequiredLegalDisclaimers.detailsMayChange),
                  const SizedBox(height: 4),
                  const Text(RequiredLegalDisclaimers.unofficialPayments),
                  const SizedBox(height: 12),
                  Text(
                    opportunity.title,
                    style: Theme.of(context).textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '${opportunity.provider}  |  ${opportunity.hostCountry}',
                  ),
                  const SizedBox(height: 4),
                  Text('Hosted by ${opportunity.hostInstitution}'),
                  const SizedBox(height: 12),
                  _DeadlineBanner(deadline: opportunity.deadline),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      Chip(label: Text(opportunity.typeLabel)),
                      Chip(label: Text(opportunity.fundingLabel)),
                      Chip(label: Text(opportunity.deliveryLabel)),
                      Chip(
                        label: Text(
                          opportunity.applicationFee == 0
                              ? 'No application fee'
                              : 'Application fee applies',
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  EligibilityMatchPanel(
                    match: const EligibilityMatcher().evaluate(
                      profile,
                      opportunity,
                    ),
                  ),
                  const SizedBox(height: 24),
                  DocumentReadinessPanel(
                    userId: userId,
                    opportunity: opportunity,
                    repository: documentRepository,
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Overview',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(opportunity.summary),
                  const SizedBox(height: 16),
                  Text('Fields: ${opportunity.fieldsOfStudy.join(', ')}'),
                  Text(
                    'Eligible nationalities: '
                    '${opportunity.eligibleNationalities.join(', ')}',
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Funding and benefits',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(opportunity.fundingLabel),
                  ...opportunity.benefits.map(
                    (benefit) => ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.check_circle_outline),
                      title: Text(benefit),
                    ),
                  ),
                  const SizedBox(height: 12),
                  _DetailSection(
                    title: 'Eligibility',
                    items: opportunity.eligibilityRequirements,
                    icon: Icons.check_circle_outline,
                  ),
                  _DetailSection(
                    title: 'Required documents',
                    items: opportunity.requiredDocuments,
                    icon: Icons.description_outlined,
                  ),
                  _DetailSection(
                    title: 'How to apply',
                    items: opportunity.applicationProcedure,
                    numbered: true,
                  ),
                  _DetailSection(
                    title: 'Language requirements',
                    items: opportunity.languageRequirements,
                    icon: Icons.language_outlined,
                  ),
                  Text(
                    'Contact: ${opportunity.contactInformation}',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Application link',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  SelectableText(opportunity.applicationUrl),
                  const SizedBox(height: 24),
                  Text(
                    'Official source',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  SelectableText(opportunity.officialSourceUrl),
                  const SizedBox(height: 36),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: () async {
                        await applicationRepository.saveOpportunity(
                          userId,
                          opportunity,
                        );
                        if (!context.mounted) return;
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text(
                              'Opportunity saved to your application tracker.',
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.bookmark_add_outlined),
                      label: const Text('Save opportunity'),
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

  static String _verificationText(Opportunity opportunity) {
    final date = opportunity.lastVerifiedAt;
    if (date == null) return opportunity.verificationLabel;
    return 'Verified from the official source on '
        '${date.day} ${_monthName(date.month)} ${date.year}.';
  }

  static String _monthName(int month) => const [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ][month - 1];
}

class _DeadlineBanner extends StatelessWidget {
  const _DeadlineBanner({required this.deadline});
  final DateTime deadline;

  @override
  Widget build(BuildContext context) {
    final daysLeft = deadline.difference(DateTime.now()).inDays;
    final closingSoon = daysLeft <= 14;
    final passed = daysLeft < 0;
    final scheme = Theme.of(context).colorScheme;
    final tone = passed || closingSoon ? scheme.error : scheme.primary;
    final formatted =
        '${deadline.day.toString().padLeft(2, '0')} '
        '${OpportunityDetailScreen._monthName(deadline.month)} '
        '${deadline.year}';
    final label = passed
        ? 'Deadline passed · $formatted'
        : closingSoon
        ? 'Closing soon · $daysLeft day${daysLeft == 1 ? '' : 's'} left · $formatted'
        : 'Deadline: $formatted';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: tone.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            passed || closingSoon ? Icons.schedule : Icons.event_outlined,
            size: 18,
            color: tone,
          ),
          const SizedBox(width: 8),
          Text(
            label,
            style: TextStyle(color: tone, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _DetailSection extends StatelessWidget {
  const _DetailSection({
    required this.title,
    required this.items,
    this.icon,
    this.numbered = false,
  });

  final String title;
  final List<String> items;
  final IconData? icon;
  final bool numbered;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          for (var index = 0; index < items.length; index++)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: numbered
                  ? CircleAvatar(radius: 14, child: Text('${index + 1}'))
                  : Icon(icon),
              title: Text(items[index]),
            ),
        ],
      ),
    );
  }
}
