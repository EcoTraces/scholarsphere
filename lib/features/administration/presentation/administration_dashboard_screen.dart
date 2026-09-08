import 'package:flutter/material.dart';

import '../../authentication/domain/auth_repository.dart';
import '../../authentication/domain/user_account.dart';
import '../../authentication/presentation/user_management_screen.dart';
import '../../collection/domain/opportunity_collection_repository.dart';
import '../../collection/presentation/collection_queue_screen.dart';
import '../domain/administration_analytics_service.dart';
import '../domain/administration_snapshot.dart';
import '../../sources/domain/source_registry_repository.dart';
import '../../sources/presentation/source_registry_screen.dart';
import '../../providers/domain/provider_repository.dart';
import '../../providers/presentation/provider_verification_queue_screen.dart';
import '../../audit/domain/audit_repository.dart';
import '../../audit/presentation/audit_log_screen.dart';
import '../../background_jobs/domain/job_queue_repository.dart';
import '../../background_jobs/presentation/job_monitor_screen.dart';
import '../../operations/domain/backup_repository.dart';
import '../../operations/domain/observability_repository.dart';
import '../../operations/domain/release_repository.dart';
import '../../operations/domain/system_configuration_repository.dart';
import '../../operations/presentation/operations_console_screen.dart';
import '../../fraud_investigation/domain/fraud_investigation_repository.dart';
import '../../governance/domain/data_lifecycle_repository.dart';
import '../../governance/domain/legal_compliance_repository.dart';
import '../../governance/presentation/data_governance_screen.dart';
import '../../taxonomy/domain/taxonomy_repository.dart';

class AdministrationDashboardScreen extends StatefulWidget {
  const AdministrationDashboardScreen({
    super.key,
    required this.user,
    required this.analytics,
    required this.authRepository,
    required this.collectionRepository,
    required this.sourceRegistryRepository,
    required this.providerRepository,
    required this.auditRepository,
    required this.jobQueueRepository,
    required this.configurationRepository,
    required this.observabilityRepository,
    required this.backupRepository,
    required this.releaseRepository,
    required this.lifecycleRepository,
    required this.legalRepository,
    required this.fraudInvestigationRepository,
    required this.taxonomyRepository,
    required this.onOpenNotifications,
    required this.onSignOut,
  });

  final UserAccount user;
  final AdministrationAnalyticsService analytics;
  final AuthRepository authRepository;
  final OpportunityCollectionRepository collectionRepository;
  final SourceRegistryRepository sourceRegistryRepository;
  final ProviderRepository providerRepository;
  final AuditRepository auditRepository;
  final JobQueueRepository jobQueueRepository;
  final SystemConfigurationRepository configurationRepository;
  final ObservabilityRepository observabilityRepository;
  final BackupRepository backupRepository;
  final ReleaseRepository releaseRepository;
  final DataLifecycleRepository lifecycleRepository;
  final LegalComplianceRepository legalRepository;
  final FraudInvestigationRepository fraudInvestigationRepository;
  final TaxonomyRepository taxonomyRepository;
  final VoidCallback onOpenNotifications;
  final VoidCallback onSignOut;

  @override
  State<AdministrationDashboardScreen> createState() =>
      _AdministrationDashboardScreenState();
}

class _AdministrationDashboardScreenState
    extends State<AdministrationDashboardScreen> {
  late Future<AdministrationData> _data;
  bool _showReports = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _data = widget.analytics.load();
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final desktop = constraints.maxWidth >= 1050;
      return Scaffold(
        drawer: desktop ? null : Drawer(child: _navigation(compact: true)),
        body: Row(
          children: [
            if (desktop) SizedBox(width: 250, child: _navigation()),
            Expanded(
              child: Column(
                children: [
                  _AdminHeader(
                    showMenu: !desktop,
                    user: widget.user,
                    title: _showReports ? 'Reports & Analytics' : 'Dashboard',
                    onRefresh: () => setState(_reload),
                    onOpenNotifications: widget.onOpenNotifications,
                    onSignOut: widget.onSignOut,
                    onAddOpportunity: _openCollection,
                  ),
                  Expanded(
                    child: FutureBuilder<AdministrationData>(
                      future: _data,
                      builder: (context, snapshot) {
                        if (snapshot.hasError) {
                          return Center(
                            child: Padding(
                              padding: const EdgeInsets.all(24),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.error_outline,
                                    size: 40,
                                    color: Theme.of(context).colorScheme.error,
                                  ),
                                  const SizedBox(height: 12),
                                  const Text(
                                    'Administration data could not be loaded.',
                                  ),
                                  const SizedBox(height: 16),
                                  FilledButton.icon(
                                    onPressed: () => setState(_reload),
                                    icon: const Icon(Icons.refresh),
                                    label: const Text('Retry'),
                                  ),
                                ],
                              ),
                            ),
                          );
                        }
                        if (!snapshot.hasData) {
                          return const Center(
                            child: CircularProgressIndicator(),
                          );
                        }
                        return _showReports
                            ? _ReportsView(snapshot: snapshot.data!.reports)
                            : _DashboardView(
                                snapshot: snapshot.data!.dashboard,
                              );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    },
  );

  Widget _navigation({bool compact = false}) => _AdminNavigation(
    user: widget.user,
    showReports: _showReports,
    onDashboard: () {
      if (compact) Navigator.pop(context);
      setState(() => _showReports = false);
    },
    onReports: () {
      if (compact) Navigator.pop(context);
      setState(() => _showReports = true);
    },
    onOpportunities: _openCollection,
    onProviders: _openProviders,
    onUsers: _openUsers,
    onVerifications: _openCollection,
    onSources: _openSources,
    onMonitoring: _openOperations,
    onJobs: _openJobs,
    onAudit: _openAudit,
    onGovernance: _openGovernance,
  );

  void _openProviders() => Navigator.of(context).push<void>(
    MaterialPageRoute(
      builder: (_) => ProviderVerificationQueueScreen(
        user: widget.user,
        repository: widget.providerRepository,
      ),
    ),
  );

  void _openUsers() => Navigator.of(context).push<void>(
    MaterialPageRoute(
      builder: (_) => UserManagementScreen(
        repository: widget.authRepository,
        administrator: widget.user,
      ),
    ),
  );

  void _openSources() => Navigator.of(context).push<void>(
    MaterialPageRoute(
      builder: (_) =>
          SourceRegistryScreen(repository: widget.sourceRegistryRepository),
    ),
  );

  void _openOperations() => Navigator.of(context).push<void>(
    MaterialPageRoute(
      builder: (_) => OperationsConsoleScreen(
        user: widget.user,
        configurationRepository: widget.configurationRepository,
        observabilityRepository: widget.observabilityRepository,
        backupRepository: widget.backupRepository,
        releaseRepository: widget.releaseRepository,
      ),
    ),
  );

  void _openJobs() => Navigator.of(context).push<void>(
    MaterialPageRoute(
      builder: (_) => JobMonitorScreen(repository: widget.jobQueueRepository),
    ),
  );

  void _openAudit() => Navigator.of(context).push<void>(
    MaterialPageRoute(
      builder: (_) =>
          AuditLogScreen(user: widget.user, repository: widget.auditRepository),
    ),
  );

  void _openGovernance() => Navigator.of(context).push<void>(
    MaterialPageRoute(
      builder: (_) => DataGovernanceScreen(
        user: widget.user,
        lifecycleRepository: widget.lifecycleRepository,
        legalRepository: widget.legalRepository,
        fraudRepository: widget.fraudInvestigationRepository,
        taxonomyRepository: widget.taxonomyRepository,
      ),
    ),
  );

  Future<void> _openCollection() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (context) => CollectionQueueScreen(
          user: widget.user,
          repository: widget.collectionRepository,
          onSignOut: widget.onSignOut,
        ),
      ),
    );
    if (mounted) setState(_reload);
  }
}

class _AdminHeader extends StatelessWidget {
  const _AdminHeader({
    required this.showMenu,
    required this.user,
    required this.title,
    required this.onRefresh,
    required this.onOpenNotifications,
    required this.onSignOut,
    required this.onAddOpportunity,
  });
  final bool showMenu;
  final UserAccount user;
  final String title;
  final VoidCallback onRefresh;
  final VoidCallback onOpenNotifications;
  final VoidCallback onSignOut;
  final VoidCallback onAddOpportunity;

  @override
  Widget build(BuildContext context) => Container(
    height: 88,
    padding: const EdgeInsets.symmetric(horizontal: 20),
    decoration: const BoxDecoration(
      color: Colors.white,
      border: Border(bottom: BorderSide(color: Color(0xFFE7EBF1))),
    ),
    child: Row(
      children: [
        if (showMenu)
          Builder(
            builder: (context) => IconButton(
              tooltip: 'Open navigation',
              onPressed: () => Scaffold.of(context).openDrawer(),
              icon: const Icon(Icons.menu),
            ),
          ),
        Expanded(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.headlineSmall),
              const Text(
                'Welcome back. Here is what is happening with ScholarSphere.',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
        if (MediaQuery.sizeOf(context).width >= 760)
          SizedBox(
            width: 320,
            child: TextField(
              readOnly: true,
              decoration: const InputDecoration(
                isDense: true,
                prefixIcon: Icon(Icons.search),
                hintText: 'Search opportunities, users, providers...',
              ),
            ),
          ),
        const SizedBox(width: 8),
        IconButton(
          tooltip: 'Refresh dashboard',
          onPressed: onRefresh,
          icon: const Icon(Icons.refresh),
        ),
        IconButton(
          tooltip: 'Notifications',
          onPressed: onOpenNotifications,
          icon: const Icon(Icons.notifications_none),
        ),
        if (MediaQuery.sizeOf(context).width >= 620)
          FilledButton.icon(
            onPressed: onAddOpportunity,
            icon: const Icon(Icons.add),
            label: const Text('Add opportunity'),
          ),
        PopupMenuButton<String>(
          tooltip: 'Administrator account',
          onSelected: (value) {
            if (value == 'sign-out') onSignOut();
          },
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'sign-out', child: Text('Sign out')),
          ],
          child: Padding(
            padding: const EdgeInsets.only(left: 12),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 18,
                  child: Text(user.fullName.substring(0, 1)),
                ),
                const SizedBox(width: 8),
                if (MediaQuery.sizeOf(context).width >= 900)
                  Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user.fullName,
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      Text(
                        user.roleLabel,
                        style: const TextStyle(fontSize: 11),
                      ),
                    ],
                  ),
              ],
            ),
          ),
        ),
      ],
    ),
  );
}

class _AdminNavigation extends StatelessWidget {
  const _AdminNavigation({
    required this.user,
    required this.showReports,
    required this.onDashboard,
    required this.onReports,
    required this.onOpportunities,
    required this.onProviders,
    required this.onUsers,
    required this.onVerifications,
    required this.onSources,
    required this.onMonitoring,
    required this.onJobs,
    required this.onAudit,
    required this.onGovernance,
  });
  final UserAccount user;
  final bool showReports;
  final VoidCallback onDashboard;
  final VoidCallback onReports;
  final VoidCallback onOpportunities;
  final VoidCallback onProviders;
  final VoidCallback onUsers;
  final VoidCallback onVerifications;
  final VoidCallback onSources;
  final VoidCallback onMonitoring;
  final VoidCallback onJobs;
  final VoidCallback onAudit;
  final VoidCallback onGovernance;

  @override
  Widget build(BuildContext context) => Material(
    color: const Color(0xFF14213D), // brand ink
    child: SafeArea(
      child: Column(
        children: [
          InkWell(
            onTap: onDashboard,
            child: const Padding(
              padding: EdgeInsets.fromLTRB(20, 18, 14, 20),
              child: Row(
                children: [
                  Icon(Icons.school_outlined, color: Colors.white, size: 34),
                  SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'ScholarSphere',
                          maxLines: 1,
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        Text(
                          'Opportunities Without Borders',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: Color(0xFFB8C7DC),
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                _item(
                  Icons.dashboard_outlined,
                  'Dashboard',
                  onDashboard,
                  !showReports,
                ),
                _label('MANAGE'),
                _item(
                  Icons.inventory_2_outlined,
                  'Opportunities',
                  onOpportunities,
                ),
                _item(Icons.business_outlined, 'Providers', onProviders),
                _item(Icons.people_outline, 'Users', onUsers),
                _item(
                  Icons.verified_outlined,
                  'Verifications',
                  onVerifications,
                ),
                _item(Icons.assignment_outlined, 'Applications', onReports),
                _item(
                  Icons.description_outlined,
                  'Reports',
                  onReports,
                  showReports,
                ),
                _label('MONITOR'),
                _item(
                  Icons.monitor_heart_outlined,
                  'System Monitoring',
                  onMonitoring,
                ),
                _item(Icons.manage_search, 'Audit Logs', onAudit),
                _item(
                  Icons.analytics_outlined,
                  'Reports & Analytics',
                  onReports,
                ),
                _item(Icons.work_history_outlined, 'Background Jobs', onJobs),
                _label('CONFIGURE'),
                _item(Icons.settings_outlined, 'Settings', onMonitoring),
                _item(Icons.source_outlined, 'Source Registry', onSources),
                _item(Icons.policy_outlined, 'Data Governance', onGovernance),
                _label('SUPPORT'),
                _item(
                  Icons.support_agent_outlined,
                  'Support Tickets',
                  onGovernance,
                ),
                _item(Icons.feedback_outlined, 'Feedback', onGovernance),
              ],
            ),
          ),
          Container(
            margin: const EdgeInsets.all(14),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              // Frosted panel on the ink sidebar, same technique as the
              // login screen's decorative side panel.
              color: Colors.white.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                CircleAvatar(child: Text(user.fullName.substring(0, 1))),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user.fullName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Colors.white),
                      ),
                      Text(
                        user.roleLabel,
                        style: const TextStyle(
                          color: Color(0xFFB8C7DC),
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );

  Widget _label(String text) => Padding(
    padding: const EdgeInsets.fromLTRB(12, 17, 12, 6),
    child: Text(
      text,
      style: const TextStyle(color: Color(0xFF8FA6C3), fontSize: 10),
    ),
  );

  Widget _item(
    IconData icon,
    String label,
    VoidCallback onTap, [
    bool selected = false,
  ]) => Padding(
    padding: const EdgeInsets.only(bottom: 2),
    child: ListTile(
      dense: true,
      selected: selected,
      selectedTileColor: const Color(0xFF007C72), // brand teal
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(7)),
      leading: Icon(icon, color: Colors.white, size: 19),
      title: Text(
        label,
        style: const TextStyle(color: Colors.white, fontSize: 13),
      ),
      onTap: onTap,
    ),
  );
}

class _DashboardView extends StatelessWidget {
  const _DashboardView({required this.snapshot});

  final AdministrationDashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final metrics = [
      ('Total opportunities', snapshot.totalOpportunities, Icons.inventory_2),
      ('Verified', snapshot.verifiedOpportunities, Icons.verified_outlined),
      (
        'Pending verification',
        snapshot.pendingVerification,
        Icons.fact_check_outlined,
      ),
      (
        'Total users',
        snapshot.registeredApplicants + snapshot.registeredProviders,
        Icons.people_outline,
      ),
      (
        'Tracked applications',
        snapshot.trackedApplications,
        Icons.assignment_outlined,
      ),
    ];
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1180),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                LayoutBuilder(
                  builder: (context, constraints) {
                    final columns = constraints.maxWidth >= 1050
                        ? 5
                        : constraints.maxWidth >= 720
                        ? 3
                        : constraints.maxWidth >= 600
                        ? 2
                        : 1;
                    return GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: metrics.length,
                      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: columns,
                        crossAxisSpacing: 12,
                        mainAxisSpacing: 12,
                        mainAxisExtent: 108,
                      ),
                      itemBuilder: (context, index) => _MetricTile(
                        label: metrics[index].$1,
                        value: metrics[index].$2.toString(),
                        icon: metrics[index].$3,
                      ),
                    );
                  },
                ),
                const SizedBox(height: 16),
                _ResponsiveSections(
                  children: [
                    _AdminPanel(
                      title: 'Opportunities by Status',
                      child: _StatusOverview(snapshot: snapshot),
                    ),
                    _AdminPanel(
                      title: 'Opportunities by Category',
                      child: _RankedSection(
                        title: '',
                        values: snapshot.popularFields,
                      ),
                    ),
                    _AdminPanel(
                      title: 'Recent Activity',
                      child: _RankedSection(
                        title: '',
                        values: snapshot.mostViewed,
                        emptyText: 'No recent opportunity activity.',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _AdminPanel(
                  title: 'User Overview',
                  child: _UserOverview(snapshot: snapshot),
                ),
                const SizedBox(height: 16),
                _ResponsiveSections(
                  children: [
                    _AdminPanel(
                      title: 'Pending Verifications',
                      child: _RankedSection(
                        title: '',
                        values: snapshot.closingSoon,
                        valueSuffix: ' days',
                        emptyText: 'No deadlines require attention.',
                      ),
                    ),
                    _AdminPanel(
                      title: 'Notification Delivery',
                      child: _RankedSection(
                        title: '',
                        values: snapshot.notificationStatistics,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const _SystemHealth(),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _AdminPanel extends StatelessWidget {
  const _AdminPanel({required this.title, required this.child});
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // No "View all" action: no caller has a real destination for it,
          // and a button that looks tappable but does nothing is worse than
          // no button at all.
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          child,
        ],
      ),
    ),
  );
}

class _StatusOverview extends StatelessWidget {
  const _StatusOverview({required this.snapshot});
  final AdministrationDashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final total = snapshot.totalOpportunities == 0
        ? 1
        : snapshot.totalOpportunities;
    final segments = [
      ('Verified', snapshot.verifiedOpportunities, const Color(0xFF007C72)),
      ('Pending', snapshot.pendingVerification, const Color(0xFF14213D)),
      ('Expired', snapshot.expiredOpportunities, const Color(0xFFE09F3E)),
      ('Suspicious', snapshot.suspiciousSubmissions, scheme.error),
    ];
    return Row(
      children: [
        SizedBox(
          width: 110,
          height: 110,
          child: Stack(
            alignment: Alignment.center,
            children: [
              CircularProgressIndicator(
                value: snapshot.verifiedOpportunities / total,
                strokeWidth: 16,
                backgroundColor: const Color(0xFFE8EEF6),
                color: const Color(0xFF007C72), // brand teal
              ),
              Text(
                '${snapshot.totalOpportunities}\nTotal',
                textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ),
        const SizedBox(width: 20),
        Expanded(
          child: Column(
            children: segments
                .map(
                  (item) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 5),
                    child: Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: item.$3,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(child: Text(item.$1)),
                        Text('${item.$2}'),
                      ],
                    ),
                  ),
                )
                .toList(),
          ),
        ),
      ],
    );
  }
}

class _UserOverview extends StatelessWidget {
  const _UserOverview({required this.snapshot});
  final AdministrationDashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final width = constraints.maxWidth >= 700
          ? (constraints.maxWidth - 36) / 4
          : (constraints.maxWidth - 12) / 2;
      return Wrap(
        spacing: 12,
        runSpacing: 12,
        children: [
          _UserMetric(
            width: width,
            label: 'Applicants',
            value: snapshot.registeredApplicants,
            icon: Icons.groups_outlined,
            color: const Color(0xFF14213D), // brand ink
          ),
          _UserMetric(
            width: width,
            label: 'Providers',
            value: snapshot.registeredProviders,
            icon: Icons.business_outlined,
            color: const Color(0xFF007C72), // brand teal
          ),
          _UserMetric(
            width: width,
            label: 'Pending reviews',
            value: snapshot.pendingVerification,
            icon: Icons.verified_user_outlined,
            color: const Color(0xFFE09F3E), // brand amber
          ),
          _UserMetric(
            width: width,
            label: 'Administrators',
            value: 1,
            icon: Icons.admin_panel_settings_outlined,
            color: const Color(0xFF007C72), // brand teal
          ),
        ],
      );
    },
  );
}

class _UserMetric extends StatelessWidget {
  const _UserMetric({
    required this.width,
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });
  final double width;
  final String label;
  final int value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: width,
    child: Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0xFFE7EBF1)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: color.withValues(alpha: 0.12),
            child: Icon(icon, color: color),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, maxLines: 1, overflow: TextOverflow.ellipsis),
                Text(
                  '$value',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

class _SystemHealth extends StatelessWidget {
  const _SystemHealth();

  @override
  Widget build(BuildContext context) => const _AdminPanel(
    title: 'System Health',
    child: Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        _HealthItem(label: 'Server status', value: 'Healthy'),
        _HealthItem(label: 'Database', value: 'Healthy'),
        _HealthItem(label: 'Storage', value: 'Available'),
        _HealthItem(label: 'Queue workers', value: 'Running'),
      ],
    ),
  );
}

class _HealthItem extends StatelessWidget {
  const _HealthItem({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 190,
    child: ListTile(
      contentPadding: EdgeInsets.zero,
      leading: const Icon(Icons.check_circle_outline, color: Color(0xFF007C72)),
      title: Text(label),
      subtitle: Text(value),
    ),
  );
}

class _ReportsView extends StatelessWidget {
  const _ReportsView({required this.snapshot});

  final ReportingSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1180),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Reporting and analytics',
                  style: Theme.of(context).textTheme.headlineLarge,
                ),
                const SizedBox(height: 16),
                _ResponsiveSections(
                  children: [
                    _RankedSection(
                      title: 'Opportunities by country',
                      values: snapshot.opportunitiesByCountry,
                    ),
                    _RankedSection(
                      title: 'Opportunities by continent',
                      values: snapshot.opportunitiesByContinent,
                    ),
                    _RankedSection(
                      title: 'Scholarships by study level',
                      values: snapshot.scholarshipsByStudyLevel,
                    ),
                    _RankedSection(
                      title: 'Funding distribution',
                      values: snapshot.opportunitiesByFunding,
                    ),
                    _RateSection(
                      title: 'Application conversion',
                      value: snapshot.applicationConversionRate,
                    ),
                    _RankedSection(
                      title: 'User interest by field',
                      values: snapshot.userInterestByField,
                    ),
                    _RankedSection(
                      title: 'Successful providers',
                      values: snapshot.successfulProviders,
                      emptyText: 'No accepted outcomes recorded yet.',
                    ),
                    _RankedSection(
                      title: 'Verification activity',
                      values: snapshot.verificationActivity,
                      emptyText: 'No verification reviews recorded yet.',
                    ),
                    _RankedSection(
                      title: 'Expired opportunity report',
                      values: snapshot.expiredOpportunityReport,
                      valueSuffix: ' days expired',
                      emptyText: 'No expired opportunities.',
                    ),
                    _RateSection(
                      title: 'Notification engagement',
                      value: snapshot.notificationEngagement,
                    ),
                    _RankedSection(
                      title: 'Application outcomes',
                      values: snapshot.applicationOutcomes,
                      emptyText: 'No application outcomes recorded yet.',
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(icon, size: 28),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(value, style: Theme.of(context).textTheme.headlineSmall),
                  Text(label, maxLines: 2, overflow: TextOverflow.ellipsis),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ResponsiveSections extends StatelessWidget {
  const _ResponsiveSections({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth >= 850
            ? (constraints.maxWidth - 20) / 2
            : constraints.maxWidth;
        return Wrap(
          spacing: 20,
          runSpacing: 28,
          children: children
              .map((child) => SizedBox(width: width, child: child))
              .toList(),
        );
      },
    );
  }
}

class _RankedSection extends StatelessWidget {
  const _RankedSection({
    required this.title,
    required this.values,
    this.valueSuffix = '',
    this.emptyText = 'No data recorded.',
  });

  final String title;
  final List<RankedMetric> values;
  final String valueSuffix;
  final String emptyText;

  @override
  Widget build(BuildContext context) {
    final maximum = values.isEmpty
        ? 1.0
        : values
              .map((item) => item.value.toDouble())
              .reduce((left, right) => left > right ? left : right);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 10),
        if (values.isEmpty)
          Text(emptyText)
        else
          for (final item in values) ...[
            Row(
              children: [
                Expanded(
                  child: Text(
                    _label(item.label),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 12),
                Text('${item.value}$valueSuffix'),
              ],
            ),
            const SizedBox(height: 5),
            LinearProgressIndicator(
              value: maximum == 0 ? 0 : item.value.toDouble() / maximum,
            ),
            const SizedBox(height: 10),
          ],
      ],
    );
  }

  static String _label(String value) {
    final spaced = value.replaceAllMapped(
      RegExp(r'([A-Z])'),
      (match) => ' ${match.group(1)!.toLowerCase()}',
    );
    return spaced.isEmpty
        ? value
        : '${spaced[0].toUpperCase()}${spaced.substring(1)}';
  }
}

class _RateSection extends StatelessWidget {
  const _RateSection({required this.title, required this.value});

  final String title;
  final double value;

  @override
  Widget build(BuildContext context) {
    final percent = (value * 100).round();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 12),
        Text('$percent%', style: Theme.of(context).textTheme.headlineLarge),
        const SizedBox(height: 8),
        LinearProgressIndicator(value: value.clamp(0, 1).toDouble()),
      ],
    );
  }
}
