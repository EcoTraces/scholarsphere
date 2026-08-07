import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../../fraud_investigation/domain/fraud_investigation_repository.dart';
import '../../taxonomy/domain/taxonomy.dart';
import '../../taxonomy/domain/taxonomy_repository.dart';
import '../domain/data_lifecycle_repository.dart';
import '../domain/legal_compliance.dart';
import '../domain/legal_compliance_repository.dart';

class DataGovernanceScreen extends StatelessWidget {
  const DataGovernanceScreen({
    super.key,
    required this.user,
    required this.lifecycleRepository,
    required this.legalRepository,
    required this.fraudRepository,
    required this.taxonomyRepository,
  });
  final UserAccount user;
  final DataLifecycleRepository lifecycleRepository;
  final LegalComplianceRepository legalRepository;
  final FraudInvestigationRepository fraudRepository;
  final TaxonomyRepository taxonomyRepository;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Data governance')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        _ActionTile(
          icon: Icons.archive_outlined,
          title: 'Retention and cleanup',
          subtitle: 'Archive, deletion, legal holds, and verification',
          onTap: () => _cleanup(context),
        ),
        _ActionTile(
          icon: Icons.policy_outlined,
          title: 'Legal policies and compliance',
          subtitle: RequiredLegalDisclaimers.noGuarantee,
          onTap: () => _legal(context),
        ),
        _ActionTile(
          icon: Icons.gpp_maybe_outlined,
          title: 'Fraud investigations',
          subtitle: 'Cases, restrictions, watchlists, and appeals',
          onTap: () => _fraud(context),
        ),
        _ActionTile(
          icon: Icons.account_tree_outlined,
          title: 'Reference taxonomy',
          subtitle: 'Canonical terms, synonyms, duplicates, and versions',
          onTap: () => _taxonomy(context),
        ),
      ],
    ),
  );

  Future<void> _cleanup(BuildContext context) async {
    final report = await lifecycleRepository.runCleanup(user);
    if (!context.mounted) return;
    _show(
      context,
      'Cleanup complete',
      '${report.archived} archived, ${report.permanentlyDeleted} deleted, '
          '${report.skippedLegalHolds} protected by legal holds.',
    );
  }

  Future<void> _legal(BuildContext context) async {
    final requests = await legalRepository.legalRequests();
    final compliance = await legalRepository.complianceRecords();
    if (!context.mounted) return;
    _show(
      context,
      'Legal compliance',
      '${requests.length} legal requests and ${compliance.length} compliance records.',
    );
  }

  Future<void> _fraud(BuildContext context) async {
    final analytics = await fraudRepository.analytics();
    if (!context.mounted) return;
    _show(
      context,
      'Fraud risk',
      '${analytics.openCases} open cases, ${analytics.criticalCases} critical, '
          '${analytics.watchlistEntries} watchlist entries.',
    );
  }

  Future<void> _taxonomy(BuildContext context) async {
    final fields = await taxonomyRepository.list(TaxonomyType.academicField);
    final duplicates = await taxonomyRepository.duplicateCandidates(
      TaxonomyType.academicField,
    );
    if (!context.mounted) return;
    _show(
      context,
      'Academic taxonomy',
      '${fields.length} canonical fields and ${duplicates.length} duplicate groups.',
    );
  }

  void _show(BuildContext context, String title, String message) {
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(title: Text(title), content: Text(message)),
    );
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      leading: Icon(icon),
      title: Text(title),
      subtitle: Text(subtitle),
      trailing: const Icon(Icons.chevron_right),
      onTap: onTap,
    ),
  );
}
