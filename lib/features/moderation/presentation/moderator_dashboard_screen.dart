import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../domain/moderation_case.dart';
import '../domain/moderation_repository.dart';
import 'moderation_queue_screen.dart';

class ModeratorDashboardScreen extends StatefulWidget {
  const ModeratorDashboardScreen({
    super.key,
    required this.user,
    required this.repository,
    required this.onSignOut,
  });
  final UserAccount user;
  final ModerationRepository repository;
  final VoidCallback onSignOut;

  @override
  State<ModeratorDashboardScreen> createState() =>
      _ModeratorDashboardScreenState();
}

class _ModeratorDashboardScreenState extends State<ModeratorDashboardScreen> {
  late Future<_ModeratorData> _data;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _data = _load();

  Future<_ModeratorData> _load() async => _ModeratorData(
    cases: await widget.repository.getQueue(),
    analytics: await widget.repository.analytics(),
  );

  void _openQueue() {
    Navigator.of(context)
        .push<void>(
          MaterialPageRoute(
            builder: (_) => ModerationQueueScreen(
              user: widget.user,
              repository: widget.repository,
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
                  _ModeratorHeader(
                    showMenu: !desktop,
                    user: widget.user,
                    onRefresh: () => setState(_reload),
                    onSignOut: widget.onSignOut,
                  ),
                  Expanded(
                    child: FutureBuilder<_ModeratorData>(
                      future: _data,
                      builder: (context, snapshot) {
                        if (!snapshot.hasData) {
                          return const Center(
                            child: CircularProgressIndicator(),
                          );
                        }
                        return _ModeratorDashboard(
                          data: snapshot.data!,
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

  Widget _navigation() =>
      _ModeratorNavigation(user: widget.user, onQueue: _openQueue);
}

class _ModeratorData {
  const _ModeratorData({required this.cases, required this.analytics});
  final List<ModerationCase> cases;
  final ModerationAnalytics analytics;
}

class _ModeratorHeader extends StatelessWidget {
  const _ModeratorHeader({
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
    height: 84,
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
                'Moderator Dashboard',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const Text(
                'Review reports, manage content, and keep the community safe.',
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
                hintText: 'Search reports...',
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
          tooltip: 'Moderator account',
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

class _ModeratorNavigation extends StatelessWidget {
  const _ModeratorNavigation({required this.user, required this.onQueue});
  final UserAccount user;
  final VoidCallback onQueue;

  @override
  Widget build(BuildContext context) => Material(
    color: const Color(0xFF17133F),
    child: SafeArea(
      child: Column(
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 18, 14, 20),
            child: Row(
              children: [
                Icon(
                  Icons.admin_panel_settings_outlined,
                  color: Color(0xFFB58CFF),
                  size: 36,
                ),
                SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'ScholarSphere',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        'Moderator Portal',
                        style: TextStyle(
                          color: Color(0xFFC8BDE8),
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                _moderatorNav(
                  Icons.dashboard_outlined,
                  'Dashboard',
                  () {},
                  true,
                ),
                _moderatorNav(Icons.flag_outlined, 'Reports', onQueue),
                _moderatorNav(Icons.pending_actions, 'Pending Review', onQueue),
                _moderatorNav(
                  Icons.manage_search,
                  'Under Investigation',
                  onQueue,
                ),
                _moderatorNav(Icons.check_circle_outline, 'Resolved', onQueue),
                _moderatorNav(
                  Icons.article_outlined,
                  'Content Management',
                  onQueue,
                ),
                _moderatorNav(
                  Icons.people_outline,
                  'Users & Providers',
                  onQueue,
                ),
                _moderatorNav(Icons.block_outlined, 'Spam & Abuse', onQueue),
                _moderatorNav(
                  Icons.campaign_outlined,
                  'Announcements',
                  onQueue,
                ),
                _moderatorNav(Icons.history_outlined, 'Audit Logs', onQueue),
                _moderatorNav(Icons.settings_outlined, 'Settings', onQueue),
                const SizedBox(height: 22),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF292455),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Need Guidelines?',
                        style: TextStyle(color: Colors.white),
                      ),
                      SizedBox(height: 10),
                      Text(
                        'Community Standards',
                        style: TextStyle(color: Color(0xFFC8BDE8)),
                      ),
                      Text(
                        'Moderation Guidelines',
                        style: TextStyle(color: Color(0xFFC8BDE8)),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Container(
            margin: const EdgeInsets.all(14),
            padding: const EdgeInsets.all(12),
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
                      const Text(
                        'Moderator • Online',
                        style: TextStyle(
                          color: Color(0xFFC8BDE8),
                          fontSize: 10,
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
}

class _ModeratorDashboard extends StatelessWidget {
  const _ModeratorDashboard({required this.data, required this.onOpenQueue});
  final _ModeratorData data;
  final VoidCallback onOpenQueue;

  @override
  Widget build(BuildContext context) {
    int count(ModerationStatus status) =>
        data.cases.where((item) => item.status == status).length;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1300),
            child: Column(
              children: [
                _ModeratorMetrics(
                  total: data.analytics.totalReports,
                  pending: data.analytics.openReports,
                  investigating: count(ModerationStatus.underReview),
                  resolved: count(ModerationStatus.resolved),
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
                          child: _ReportsByCategory(cases: data.cases),
                        ),
                        SizedBox(
                          width: width,
                          child: _ReportsTrend(cases: data.cases),
                        ),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 16),
                _RecentReports(cases: data.cases, onOpen: onOpenQueue),
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
                          child: _ContentActions(analytics: data.analytics),
                        ),
                        SizedBox(
                          width: width,
                          child: _TopReported(cases: data.cases),
                        ),
                        SizedBox(
                          width: width,
                          child: const _CommunityReminders(),
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

class _ModeratorMetrics extends StatelessWidget {
  const _ModeratorMetrics({
    required this.total,
    required this.pending,
    required this.investigating,
    required this.resolved,
  });
  final int total;
  final int pending;
  final int investigating;
  final int resolved;

  @override
  Widget build(BuildContext context) => _ModeratorMetricWrap(
    metrics: [
      ('New Reports', total, Icons.flag_outlined, const Color(0xFF7047EB)),
      (
        'Pending Review',
        pending,
        Icons.pending_actions,
        const Color(0xFFFF7A21),
      ),
      (
        'Under Investigation',
        investigating,
        Icons.shield_outlined,
        const Color(0xFFE83B55),
      ),
      (
        'Resolved This Week',
        resolved,
        Icons.check_circle_outline,
        const Color(0xFF16B76A),
      ),
    ],
  );
}

class _ReportsByCategory extends StatelessWidget {
  const _ReportsByCategory({required this.cases});
  final List<ModerationCase> cases;

  @override
  Widget build(BuildContext context) {
    final counts = <ModerationReportType, int>{};
    for (final item in cases) {
      counts.update(item.reportType, (value) => value + 1, ifAbsent: () => 1);
    }
    return _ModeratorPanel(
      title: 'Reports by Category',
      child: Row(
        children: [
          _ModeratorRing(value: cases.length, label: 'Total'),
          const SizedBox(width: 18),
          Expanded(
            child: Column(
              children: counts.entries
                  .take(6)
                  .map(
                    (entry) => _moderatorValueRow(
                      _moderatorLabel(entry.key.name),
                      entry.value,
                    ),
                  )
                  .toList(),
            ),
          ),
        ],
      ),
    );
  }
}

class _ReportsTrend extends StatelessWidget {
  const _ReportsTrend({required this.cases});
  final List<ModerationCase> cases;

  @override
  Widget build(BuildContext context) => _ModeratorPanel(
    title: 'Reports Trend',
    child: SizedBox(
      height: 145,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: List.generate(7, (index) {
          final count = cases
              .where((item) => item.createdAt.weekday == index + 1)
              .length;
          return Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 6),
              child: Container(
                height: 24 + count * 20,
                decoration: const BoxDecoration(
                  color: Color(0xFF7047EB),
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

class _RecentReports extends StatelessWidget {
  const _RecentReports({required this.cases, required this.onOpen});
  final List<ModerationCase> cases;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) => _ModeratorPanel(
    title: 'Recent Reports',
    child: cases.isEmpty
        ? const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: Text('No moderation reports require review.'),
          )
        : Column(
            children: cases
                .take(7)
                .map(
                  (item) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const CircleAvatar(
                      child: Icon(Icons.flag_outlined),
                    ),
                    title: Text(_moderatorLabel(item.reportType.name)),
                    subtitle: Text(
                      '${item.entityType.name}: ${item.entityId} • ${item.reporterId}',
                    ),
                    trailing: Chip(
                      label: Text(_moderatorLabel(item.status.name)),
                    ),
                    onTap: onOpen,
                  ),
                )
                .toList(),
          ),
  );
}

class _ContentActions extends StatelessWidget {
  const _ContentActions({required this.analytics});
  final ModerationAnalytics analytics;

  @override
  Widget build(BuildContext context) => _ModeratorPanel(
    title: 'Content Actions',
    child: Column(
      children: [
        _moderatorValueRow('Content Removed', analytics.removedContent),
        _moderatorValueRow('Providers Suspended', analytics.suspendedProviders),
        _moderatorValueRow('Open Reports', analytics.openReports),
        _moderatorValueRow(
          'Repeat Offenders',
          analytics.repeatOffenders.length,
        ),
      ],
    ),
  );
}

class _TopReported extends StatelessWidget {
  const _TopReported({required this.cases});
  final List<ModerationCase> cases;

  @override
  Widget build(BuildContext context) {
    final values = <String, int>{};
    for (final item in cases) {
      values.update(item.entityId, (value) => value + 1, ifAbsent: () => 1);
    }
    return _ModeratorPanel(
      title: 'Top Reported Items',
      child: values.isEmpty
          ? const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Text('No repeat reports recorded.'),
            )
          : Column(
              children: values.entries
                  .take(5)
                  .map((entry) => _moderatorValueRow(entry.key, entry.value))
                  .toList(),
            ),
    );
  }
}

class _CommunityReminders extends StatelessWidget {
  const _CommunityReminders();

  @override
  Widget build(BuildContext context) => _ModeratorPanel(
    title: 'Community Reminders',
    child: Column(
      children: [
        _reminder('Be fair and consistent.'),
        _reminder('Treat everyone with respect.'),
        _reminder('Escalate serious issues.'),
        _reminder('Keep the community safe.'),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: () {},
            child: const Text('View Community Standards'),
          ),
        ),
      ],
    ),
  );
}

class _ModeratorMetricWrap extends StatelessWidget {
  const _ModeratorMetricWrap({required this.metrics});
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
                height: 112,
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
                              Text(metric.$1, maxLines: 2),
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

class _ModeratorPanel extends StatelessWidget {
  const _ModeratorPanel({required this.title, required this.child});
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

class _ModeratorRing extends StatelessWidget {
  const _ModeratorRing({required this.value, required this.label});
  final int value;
  final String label;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 120,
    height: 120,
    child: Stack(
      alignment: Alignment.center,
      children: [
        const CircularProgressIndicator(
          value: 0.72,
          strokeWidth: 14,
          backgroundColor: Color(0xFFE7EBF1),
          color: Color(0xFF7047EB),
        ),
        Text('$value\n$label', textAlign: TextAlign.center),
      ],
    ),
  );
}

Widget _moderatorNav(
  IconData icon,
  String label,
  VoidCallback onTap, [
  bool selected = false,
]) => Padding(
  padding: const EdgeInsets.only(bottom: 3),
  child: ListTile(
    dense: true,
    selected: selected,
    selectedTileColor: const Color(0xFF6338B8),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(7)),
    leading: Icon(icon, color: Colors.white, size: 19),
    title: Text(
      label,
      style: const TextStyle(color: Colors.white, fontSize: 13),
    ),
    onTap: onTap,
  ),
);

Widget _moderatorValueRow(String label, int value) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 7),
  child: Row(
    children: [
      Expanded(child: Text(label, overflow: TextOverflow.ellipsis)),
      Text('$value'),
    ],
  ),
);

Widget _reminder(String text) => ListTile(
  dense: true,
  contentPadding: EdgeInsets.zero,
  leading: const Icon(Icons.shield_outlined, color: Color(0xFF7047EB)),
  title: Text(text),
);

String _moderatorLabel(String value) => value
    .replaceAllMapped(
      RegExp(r'([A-Z])'),
      (match) => ' ${match.group(1)!.toLowerCase()}',
    )
    .replaceFirstMapped(
      RegExp(r'^.'),
      (match) => match.group(0)!.toUpperCase(),
    );
