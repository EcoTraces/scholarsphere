import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../../fraud/domain/fraud_detection_service.dart';
import '../../opportunities/domain/opportunity.dart';
import '../../providers/domain/provider_repository.dart';
import '../domain/verification_repository.dart';
import '../domain/verification_review.dart';
import 'verification_queue_screen.dart';

class VerificationOfficerDashboardScreen extends StatefulWidget {
  const VerificationOfficerDashboardScreen({
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
  State<VerificationOfficerDashboardScreen> createState() =>
      _VerificationOfficerDashboardScreenState();
}

class _VerificationOfficerDashboardScreenState
    extends State<VerificationOfficerDashboardScreen> {
  late Future<_VerificationData> _data;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _data = _load();

  Future<_VerificationData> _load() async => _VerificationData(
    queue: await widget.repository.getQueue(),
    reviews: await widget.repository.getAllForAdministration(),
  );

  void _openQueue() {
    Navigator.of(context)
        .push<void>(
          MaterialPageRoute(
            builder: (_) => VerificationQueueScreen(
              user: widget.user,
              repository: widget.repository,
              providerRepository: widget.providerRepository,
              onSignOut: widget.onSignOut,
            ),
          ),
        )
        .then((_) {
          if (mounted) setState(_reload);
        });
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final desktop = constraints.maxWidth >= 1050;
      return Scaffold(
        drawer: desktop ? null : Drawer(child: _navigation()),
        body: Row(
          children: [
            if (desktop) SizedBox(width: 250, child: _navigation()),
            Expanded(
              child: Column(
                children: [
                  _OfficerHeader(
                    showMenu: !desktop,
                    user: widget.user,
                    onRefresh: () => setState(_reload),
                    onSignOut: widget.onSignOut,
                  ),
                  Expanded(
                    child: FutureBuilder<_VerificationData>(
                      future: _data,
                      builder: (context, snapshot) {
                        if (!snapshot.hasData) {
                          return const Center(
                            child: CircularProgressIndicator(),
                          );
                        }
                        return _VerificationDashboard(
                          data: snapshot.data!,
                          officerId: widget.user.id,
                          onOpenQueue: _openQueue,
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

  Widget _navigation() => _OfficerNavigation(
    user: widget.user,
    onQueue: _openQueue,
    onSignOut: widget.onSignOut,
  );
}

class _VerificationData {
  const _VerificationData({required this.queue, required this.reviews});
  final List<Opportunity> queue;
  final List<VerificationReview> reviews;
}

class _OfficerHeader extends StatelessWidget {
  const _OfficerHeader({
    required this.showMenu,
    required this.user,
    required this.onRefresh,
    required this.onSignOut,
  });
  final bool showMenu;
  final UserAccount user;
  final VoidCallback onRefresh;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) => Container(
    height: 104,
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
              Text(
                'Security Verification Officer Dashboard',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const Text(
                'Verify opportunities and ensure trust, accuracy, and authenticity.',
              ),
            ],
          ),
        ),
        if (MediaQuery.sizeOf(context).width >= 720)
          const SizedBox(
            width: 300,
            child: TextField(
              readOnly: true,
              decoration: InputDecoration(
                isDense: true,
                prefixIcon: Icon(Icons.search),
                hintText: 'Search opportunities...',
              ),
            ),
          ),
        IconButton(
          tooltip: 'Refresh dashboard',
          onPressed: onRefresh,
          icon: const Icon(Icons.refresh),
        ),
        IconButton(
          tooltip: 'Notifications',
          onPressed: () {},
          icon: const Icon(Icons.notifications_none),
        ),
        PopupMenuButton<String>(
          tooltip: 'Verification officer account',
          onSelected: (value) {
            if (value == 'sign-out') onSignOut();
          },
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'sign-out', child: Text('Sign out')),
          ],
          child: CircleAvatar(child: Text(user.fullName.substring(0, 1))),
        ),
      ],
    ),
  );
}

class _OfficerNavigation extends StatelessWidget {
  const _OfficerNavigation({
    required this.user,
    required this.onQueue,
    required this.onSignOut,
  });
  final UserAccount user;
  final VoidCallback onQueue;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) => Material(
    color: const Color(0xFF06244A),
    child: SafeArea(
      child: Column(
        children: [
          const _RoleBrand(
            icon: Icons.shield_outlined,
            subtitle: 'Opportunities Without Borders',
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                _nav(Icons.dashboard_outlined, 'Dashboard', () {}, true),
                _section('VERIFICATION'),
                _nav(Icons.fact_check_outlined, 'Verification Queue', onQueue),
                _nav(Icons.assignment_ind_outlined, 'My Assignments', onQueue),
                _nav(Icons.rate_review_outlined, 'Under Review', onQueue),
                _nav(Icons.upload_file_outlined, 'Awaiting Evidence', onQueue),
                _nav(Icons.verified_outlined, 'Verified Today', onQueue),
                _nav(
                  Icons.event_repeat_outlined,
                  'Reverification Due',
                  onQueue,
                ),
                _nav(Icons.inventory_2_outlined, 'All Opportunities', onQueue),
                _nav(Icons.source_outlined, 'Source Check', onQueue),
                _section('SECURITY'),
                _nav(Icons.warning_amber_outlined, 'Risk Alerts', onQueue),
                _nav(Icons.manage_search, 'Fraud Detection', onQueue),
                _nav(Icons.shield_outlined, 'Source Reliability', onQueue),
                _section('REPORTS'),
                _nav(Icons.analytics_outlined, 'Verification Reports', onQueue),
                _nav(Icons.history_outlined, 'Audit Logs', onQueue),
                _section('TOOLS'),
                _nav(Icons.menu_book_outlined, 'Guidelines', onQueue),
                _nav(Icons.checklist_outlined, 'Checklists', onQueue),
                _nav(Icons.settings_outlined, 'Settings', onQueue),
              ],
            ),
          ),
          _RoleIdentity(user: user, role: 'Verification Officer'),
        ],
      ),
    ),
  );
}

class _VerificationDashboard extends StatelessWidget {
  const _VerificationDashboard({
    required this.data,
    required this.officerId,
    required this.onOpenQueue,
  });
  final _VerificationData data;
  final String officerId;
  final VoidCallback onOpenQueue;

  @override
  Widget build(BuildContext context) {
    final assigned = data.reviews
        .where((review) => review.assignedToUserId == officerId)
        .length;
    final verified = data.reviews
        .where(
          (review) =>
              review.workflowStatus == VerificationWorkflowStatus.verified,
        )
        .length;
    final due = data.reviews
        .where(
          (review) =>
              review.nextReviewAt != null &&
              review.nextReviewAt!.isBefore(
                DateTime.now().add(const Duration(days: 7)),
              ),
        )
        .length;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1300),
            child: Column(
              children: [
                _OfficerMetrics(
                  pending: data.queue.length,
                  assigned: assigned,
                  verified: verified,
                  due: due,
                ),
                const SizedBox(height: 16),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final width = constraints.maxWidth >= 800
                        ? (constraints.maxWidth - 16) / 2
                        : constraints.maxWidth;
                    return Wrap(
                      spacing: 16,
                      runSpacing: 16,
                      children: [
                        SizedBox(
                          width: width,
                          child: _QueueOverview(
                            queue: data.queue,
                            reviews: data.reviews,
                          ),
                        ),
                        SizedBox(
                          width: width,
                          child: _VerificationActivity(reviews: data.reviews),
                        ),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 16),
                _AssignmentTable(
                  opportunities: data.queue,
                  onOpen: onOpenQueue,
                ),
                const SizedBox(height: 16),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final width = constraints.maxWidth >= 840
                        ? (constraints.maxWidth - 32) / 3
                        : constraints.maxWidth;
                    return Wrap(
                      spacing: 16,
                      runSpacing: 16,
                      children: [
                        SizedBox(
                          width: width,
                          child: _SourceReliability(reviews: data.reviews),
                        ),
                        SizedBox(
                          width: width,
                          child: _StatusTrend(reviews: data.reviews),
                        ),
                        SizedBox(
                          width: width,
                          child: _RiskAlerts(queue: data.queue),
                        ),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _OfficerMetrics extends StatelessWidget {
  const _OfficerMetrics({
    required this.pending,
    required this.assigned,
    required this.verified,
    required this.due,
  });
  final int pending;
  final int assigned;
  final int verified;
  final int due;

  @override
  Widget build(BuildContext context) => _MetricWrap(
    metrics: [
      (
        'Pending Verification',
        pending,
        Icons.pending_actions,
        const Color(0xFF2878F0),
      ),
      (
        'My Assignments',
        assigned,
        Icons.assignment_ind_outlined,
        const Color(0xFF7047EB),
      ),
      (
        'Verified Today',
        verified,
        Icons.verified_outlined,
        const Color(0xFF16B76A),
      ),
      (
        'Reverification Due',
        due,
        Icons.event_repeat_outlined,
        const Color(0xFFFF7A21),
      ),
    ],
  );
}

class _QueueOverview extends StatelessWidget {
  const _QueueOverview({required this.queue, required this.reviews});
  final List<Opportunity> queue;
  final List<VerificationReview> reviews;

  @override
  Widget build(BuildContext context) => _RolePanel(
    title: 'Verification Queue Overview',
    child: Row(
      children: [
        _Ring(value: queue.length, label: 'Total', progress: 0.7),
        const SizedBox(width: 20),
        Expanded(
          child: Column(
            children: [
              _valueRow('Pending', queue.length),
              _valueRow(
                'Under Review',
                reviews
                    .where(
                      (item) =>
                          item.workflowStatus ==
                          VerificationWorkflowStatus.underReview,
                    )
                    .length,
              ),
              _valueRow(
                'Awaiting Evidence',
                reviews
                    .where(
                      (item) =>
                          item.workflowStatus ==
                          VerificationWorkflowStatus.additionalEvidenceRequired,
                    )
                    .length,
              ),
              _valueRow(
                'Verified',
                reviews
                    .where(
                      (item) =>
                          item.workflowStatus ==
                          VerificationWorkflowStatus.verified,
                    )
                    .length,
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _VerificationActivity extends StatelessWidget {
  const _VerificationActivity({required this.reviews});
  final List<VerificationReview> reviews;

  @override
  Widget build(BuildContext context) => _RolePanel(
    title: 'Verification Activity',
    child: SizedBox(
      height: 145,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: List.generate(7, (index) {
          final count = reviews
              .where((review) => review.reviewedAt.weekday == index + 1)
              .length;
          return Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 6),
              child: Container(
                height: 24 + count * 18,
                decoration: const BoxDecoration(
                  color: Color(0xFF2878F0),
                  borderRadius: BorderRadius.vertical(top: Radius.circular(4)),
                ),
              ),
            ),
          );
        }),
      ),
    ),
  );
}

class _AssignmentTable extends StatelessWidget {
  const _AssignmentTable({required this.opportunities, required this.onOpen});
  final List<Opportunity> opportunities;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) => _RolePanel(
    title: 'My Recent Assignments',
    child: opportunities.isEmpty
        ? const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: Text('The verification queue is clear.'),
          )
        : Column(
            children: opportunities
                .take(6)
                .map(
                  (item) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const CircleAvatar(
                      child: Icon(Icons.school_outlined),
                    ),
                    title: Text(item.title),
                    subtitle: Text(
                      '${item.provider} • ${item.verificationLabel}',
                    ),
                    trailing: IconButton(
                      tooltip: 'Open review',
                      onPressed: onOpen,
                      icon: const Icon(Icons.visibility_outlined),
                    ),
                    onTap: onOpen,
                  ),
                )
                .toList(),
          ),
  );
}

class _SourceReliability extends StatelessWidget {
  const _SourceReliability({required this.reviews});
  final List<VerificationReview> reviews;

  @override
  Widget build(BuildContext context) {
    final official = reviews
        .where((review) => review.hasOfficialAuthority)
        .length;
    final ratio = reviews.isEmpty ? 1.0 : official / reviews.length;
    return _RolePanel(
      title: 'Source Reliability',
      child: Center(
        child: _Ring(
          value: (ratio * 100).round(),
          label: 'Average score',
          progress: ratio,
          suffix: '%',
        ),
      ),
    );
  }
}

class _StatusTrend extends StatelessWidget {
  const _StatusTrend({required this.reviews});
  final List<VerificationReview> reviews;

  @override
  Widget build(BuildContext context) => _RolePanel(
    title: 'Verification Status Trend',
    child: Column(
      children: VerificationWorkflowStatus.values
          .take(5)
          .map(
            (status) => _valueRow(
              _enumLabel(status.name),
              reviews.where((review) => review.workflowStatus == status).length,
            ),
          )
          .toList(),
    ),
  );
}

class _RiskAlerts extends StatelessWidget {
  const _RiskAlerts({required this.queue});
  final List<Opportunity> queue;

  @override
  Widget build(BuildContext context) {
    final detector = FraudDetectionService();
    final warnings = queue
        .map((item) => detector.assess(item, knownOpportunities: queue))
        .where((assessment) => assessment.hasWarnings)
        .toList();
    return _RolePanel(
      title: 'Risk Alerts',
      child: warnings.isEmpty
          ? const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Text('No automated risk alerts.'),
            )
          : Column(
              children: warnings
                  .take(4)
                  .map(
                    (assessment) => ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(
                        Icons.warning_amber,
                        color: Color(0xFFFF7A21),
                      ),
                      title: Text(assessment.levelLabel),
                      subtitle: Text(
                        assessment.signals.first.userMessage,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  )
                  .toList(),
            ),
    );
  }
}

class _MetricWrap extends StatelessWidget {
  const _MetricWrap({required this.metrics});
  final List<(String, int, IconData, Color)> metrics;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final columns = constraints.maxWidth >= 850 ? 4 : 2;
      final width = (constraints.maxWidth - (columns - 1) * 12) / columns;
      return Wrap(
        spacing: 12,
        runSpacing: 12,
        children: metrics
            .map(
              (metric) => SizedBox(
                width: width,
                height: 132,
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        CircleAvatar(
                          backgroundColor: metric.$4.withValues(alpha: 0.12),
                          child: Icon(metric.$3, color: metric.$4),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                metric.$1,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                              Text(
                                '${metric.$2}',
                                style: Theme.of(
                                  context,
                                ).textTheme.headlineSmall,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            )
            .toList(),
      );
    },
  );
}

class _RolePanel extends StatelessWidget {
  const _RolePanel({required this.title, required this.child});
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              TextButton(onPressed: () {}, child: const Text('View all')),
            ],
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    ),
  );
}

class _Ring extends StatelessWidget {
  const _Ring({
    required this.value,
    required this.label,
    required this.progress,
    this.suffix = '',
  });
  final int value;
  final String label;
  final double progress;
  final String suffix;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 120,
    height: 120,
    child: Stack(
      alignment: Alignment.center,
      children: [
        CircularProgressIndicator(
          value: progress.clamp(0, 1),
          strokeWidth: 14,
          backgroundColor: const Color(0xFFE7EBF1),
        ),
        Text('$value$suffix\n$label', textAlign: TextAlign.center),
      ],
    ),
  );
}

class _RoleBrand extends StatelessWidget {
  const _RoleBrand({required this.icon, required this.subtitle});
  final IconData icon;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(20, 18, 14, 20),
    child: Row(
      children: [
        Icon(icon, color: const Color(0xFF19BFF3), size: 36),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'ScholarSphere',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                subtitle,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Color(0xFFB8C7DC), fontSize: 9),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _RoleIdentity extends StatelessWidget {
  const _RoleIdentity({required this.user, required this.role});
  final UserAccount user;
  final String role;

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.all(14),
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: const Color(0xFF123762),
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
                '$role • Online',
                style: const TextStyle(color: Color(0xFFB8C7DC), fontSize: 10),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

Widget _section(String label) => Padding(
  padding: const EdgeInsets.fromLTRB(12, 17, 12, 6),
  child: Text(
    label,
    style: const TextStyle(color: Color(0xFF8FA6C3), fontSize: 10),
  ),
);

Widget _nav(
  IconData icon,
  String label,
  VoidCallback onTap, [
  bool selected = false,
]) => Padding(
  padding: const EdgeInsets.only(bottom: 2),
  child: ListTile(
    dense: true,
    selected: selected,
    selectedTileColor: const Color(0xFF1769FF),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(7)),
    leading: Icon(icon, color: Colors.white, size: 19),
    title: Text(
      label,
      style: const TextStyle(color: Colors.white, fontSize: 13),
    ),
    onTap: onTap,
  ),
);

Widget _valueRow(String label, int value) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 6),
  child: Row(
    children: [
      Expanded(child: Text(label)),
      Text('$value'),
    ],
  ),
);

String _enumLabel(String value) => value
    .replaceAllMapped(
      RegExp(r'([A-Z])'),
      (match) => ' ${match.group(1)!.toLowerCase()}',
    )
    .replaceFirstMapped(
      RegExp(r'^.'),
      (match) => match.group(0)!.toUpperCase(),
    );
