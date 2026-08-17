import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../domain/support_models.dart';
import '../domain/support_repository.dart';
import 'help_centre_screen.dart';

class SupportAgentScreen extends StatefulWidget {
  const SupportAgentScreen({
    super.key,
    required this.user,
    required this.repository,
    required this.onSignOut,
  });
  final UserAccount user;
  final SupportRepository repository;
  final VoidCallback onSignOut;

  @override
  State<SupportAgentScreen> createState() => _SupportAgentScreenState();
}

class _SupportAgentScreenState extends State<SupportAgentScreen> {
  late Future<_SupportDashboardData> _data;
  SupportTicketStatus? _statusFilter;
  bool _assignedOnly = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _data = _load();
  }

  Future<_SupportDashboardData> _load() async {
    final results = await Future.wait([
      widget.repository.getAgentQueue(),
      widget.repository.performanceReport(),
      widget.repository.searchKnowledge(''),
    ]);
    return _SupportDashboardData(
      tickets: results[0] as List<SupportTicket>,
      performance: results[1] as SupportPerformanceReport,
      articles: results[2] as List<KnowledgeArticle>,
    );
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
                  _SupportHeader(
                    showMenu: !desktop,
                    user: widget.user,
                    onRefresh: () => setState(_reload),
                    onSignOut: widget.onSignOut,
                  ),
                  Expanded(
                    child: FutureBuilder<_SupportDashboardData>(
                      future: _data,
                      builder: (context, snapshot) {
                        if (snapshot.hasError) {
                          return const Center(
                            child: Text('Support data could not be loaded.'),
                          );
                        }
                        if (!snapshot.hasData) {
                          return const Center(
                            child: CircularProgressIndicator(),
                          );
                        }
                        return _SupportDashboard(
                          data: snapshot.data!,
                          user: widget.user,
                          statusFilter: _statusFilter,
                          assignedOnly: _assignedOnly,
                          onFilter: (status, assignedOnly) => setState(() {
                            _statusFilter = status;
                            _assignedOnly = assignedOnly;
                          }),
                          onOpenTicket: _open,
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

  Widget _navigation({bool compact = false}) => _SupportNavigation(
    user: widget.user,
    onDashboard: () {
      if (compact) Navigator.pop(context);
      setState(() {
        _statusFilter = null;
        _assignedOnly = false;
      });
    },
    onTickets: () => setState(() {
      _statusFilter = null;
      _assignedOnly = false;
    }),
    onAssigned: () => setState(() => _assignedOnly = true),
    onOpen: () => setState(() {
      _statusFilter = SupportTicketStatus.open;
      _assignedOnly = false;
    }),
    onResolved: () => setState(() {
      _statusFilter = SupportTicketStatus.resolved;
      _assignedOnly = false;
    }),
  );

  Future<void> _open(SupportTicket ticket) async {
    if (ticket.assignedAgentId == null) {
      await widget.repository.assign(ticket.id, widget.user.id);
    }
    if (!mounted) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => SupportConversationScreen(
          ticketId: ticket.id,
          userId: widget.user.id,
          repository: widget.repository,
          isAgent: true,
        ),
      ),
    );
    if (mounted) setState(_reload);
  }
}

class _SupportDashboardData {
  const _SupportDashboardData({
    required this.tickets,
    required this.performance,
    required this.articles,
  });
  final List<SupportTicket> tickets;
  final SupportPerformanceReport performance;
  final List<KnowledgeArticle> articles;
}

class _SupportHeader extends StatelessWidget {
  const _SupportHeader({
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
                'Dashboard',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const Text('Here is your customer support overview.'),
            ],
          ),
        ),
        if (MediaQuery.sizeOf(context).width >= 720)
          SizedBox(
            width: 340,
            child: TextField(
              readOnly: true,
              decoration: const InputDecoration(
                isDense: true,
                prefixIcon: Icon(Icons.search),
                hintText: 'Search tickets, users, or keywords...',
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
        const Chip(
          avatar: Icon(Icons.circle, size: 10, color: Color(0xFF16B76A)),
          label: Text('Available'),
        ),
        PopupMenuButton<String>(
          tooltip: 'Support officer account',
          onSelected: (value) {
            if (value == 'sign-out') onSignOut();
          },
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'sign-out', child: Text('Sign out')),
          ],
          child: Padding(
            padding: const EdgeInsets.only(left: 10),
            child: CircleAvatar(child: Text(user.fullName.substring(0, 1))),
          ),
        ),
      ],
    ),
  );
}

class _SupportNavigation extends StatelessWidget {
  const _SupportNavigation({
    required this.user,
    required this.onDashboard,
    required this.onTickets,
    required this.onAssigned,
    required this.onOpen,
    required this.onResolved,
  });
  final UserAccount user;
  final VoidCallback onDashboard;
  final VoidCallback onTickets;
  final VoidCallback onAssigned;
  final VoidCallback onOpen;
  final VoidCallback onResolved;

  @override
  Widget build(BuildContext context) => Material(
    color: const Color(0xFF06244A),
    child: SafeArea(
      child: Column(
        children: [
          const Padding(
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
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        'Support Excellence',
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
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                _item(Icons.dashboard_outlined, 'Dashboard', onDashboard, true),
                _label('SUPPORT'),
                _item(Icons.inbox_outlined, 'All Tickets', onTickets),
                _item(Icons.person_pin_outlined, 'My Assigned', onAssigned),
                _item(Icons.mark_email_unread_outlined, 'Open', onOpen),
                _item(Icons.check_circle_outline, 'Resolved', onResolved),
                _item(Icons.menu_book_outlined, 'Knowledge Base', onTickets),
                _item(Icons.quickreply_outlined, 'Saved Replies', onTickets),
                _item(Icons.campaign_outlined, 'Announcements', onTickets),
                _label('USER MANAGEMENT'),
                _item(Icons.people_outline, 'Users', onTickets),
                _item(Icons.business_outlined, 'Providers', onTickets),
                _label('REPORTS'),
                _item(
                  Icons.analytics_outlined,
                  'Reports & Analytics',
                  onTickets,
                ),
                _item(Icons.speed_outlined, 'Performance', onTickets),
                _label('SETTINGS'),
                _item(
                  Icons.notifications_none,
                  'Notification Settings',
                  onTickets,
                ),
                _item(
                  Icons.manage_accounts_outlined,
                  'Account Settings',
                  onTickets,
                ),
              ],
            ),
          ),
          Container(
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
                      const Text(
                        'Support Officer • Online',
                        style: TextStyle(
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

  Widget _label(String label) => Padding(
    padding: const EdgeInsets.fromLTRB(12, 17, 12, 6),
    child: Text(
      label,
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
      selectedTileColor: const Color(0xFF263A96),
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

class _SupportDashboard extends StatelessWidget {
  const _SupportDashboard({
    required this.data,
    required this.user,
    required this.statusFilter,
    required this.assignedOnly,
    required this.onFilter,
    required this.onOpenTicket,
  });
  final _SupportDashboardData data;
  final UserAccount user;
  final SupportTicketStatus? statusFilter;
  final bool assignedOnly;
  final void Function(SupportTicketStatus?, bool) onFilter;
  final ValueChanged<SupportTicket> onOpenTicket;

  @override
  Widget build(BuildContext context) {
    var tickets = data.tickets;
    if (statusFilter != null) {
      tickets = tickets.where((item) => item.status == statusFilter).toList();
    }
    if (assignedOnly) {
      tickets = tickets
          .where((item) => item.assignedAgentId == user.id)
          .toList();
    }
    final assigned = data.tickets
        .where((item) => item.assignedAgentId == user.id)
        .length;
    final resolved = data.tickets
        .where((item) => item.status == SupportTicketStatus.resolved)
        .length;
    final waiting = data.tickets
        .where((item) => item.status == SupportTicketStatus.waitingForUser)
        .length;

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1300),
            child: Column(
              children: [
                _SupportMetrics(
                  open: data.performance.openTickets,
                  assigned: assigned,
                  resolved: resolved,
                  responseMinutes: data.performance.averageFirstResponseMinutes,
                  satisfaction: data.performance.satisfactionScore,
                ),
                const SizedBox(height: 16),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final twoColumns = constraints.maxWidth >= 900;
                    final queue = _TicketQueue(
                      tickets: tickets,
                      statusFilter: statusFilter,
                      assignedOnly: assignedOnly,
                      onFilter: onFilter,
                      onOpen: onOpenTicket,
                    );
                    final side = Column(
                      children: [
                        _ActiveChats(tickets: data.tickets),
                        const SizedBox(height: 16),
                        _KnowledgeBase(articles: data.articles),
                      ],
                    );
                    return twoColumns
                        ? Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(flex: 3, child: queue),
                              const SizedBox(width: 16),
                              Expanded(flex: 2, child: side),
                            ],
                          )
                        : Column(
                            children: [queue, const SizedBox(height: 16), side],
                          );
                  },
                ),
                const SizedBox(height: 16),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final width = constraints.maxWidth >= 780
                        ? (constraints.maxWidth - 16) / 2
                        : constraints.maxWidth;
                    return Wrap(
                      spacing: 16,
                      runSpacing: 16,
                      children: [
                        SizedBox(
                          width: width,
                          child: _TicketStatus(
                            total: data.tickets.length,
                            open: data.performance.openTickets,
                            assigned: assigned,
                            waiting: waiting,
                            resolved: resolved,
                          ),
                        ),
                        SizedBox(
                          width: width,
                          child: _CategoryChart(
                            values: data.performance.byCategory,
                          ),
                        ),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 16),
                _PerformanceOverview(report: data.performance),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _SupportMetrics extends StatelessWidget {
  const _SupportMetrics({
    required this.open,
    required this.assigned,
    required this.resolved,
    required this.responseMinutes,
    required this.satisfaction,
  });
  final int open;
  final int assigned;
  final int resolved;
  final double responseMinutes;
  final double satisfaction;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final columns = constraints.maxWidth >= 1000
          ? 5
          : constraints.maxWidth >= 620
          ? 3
          : 2;
      final width = (constraints.maxWidth - (columns - 1) * 12) / columns;
      return Wrap(
        spacing: 12,
        runSpacing: 12,
        children: [
          _SupportMetric(
            width: width,
            label: 'Open Tickets',
            value: '$open',
            icon: Icons.confirmation_number_outlined,
            color: const Color(0xFF5A3EF0),
          ),
          _SupportMetric(
            width: width,
            label: 'My Assigned',
            value: '$assigned',
            icon: Icons.person_outline,
            color: const Color(0xFF2878F0),
          ),
          _SupportMetric(
            width: width,
            label: 'Resolved Today',
            value: '$resolved',
            icon: Icons.check_circle_outline,
            color: const Color(0xFF16B76A),
          ),
          _SupportMetric(
            width: width,
            label: 'Avg. Response Time',
            value: _duration(responseMinutes),
            icon: Icons.schedule,
            color: const Color(0xFFFF7A21),
          ),
          _SupportMetric(
            width: width,
            label: 'Customer Satisfaction',
            value: '${satisfaction.toStringAsFixed(0)}%',
            icon: Icons.workspace_premium_outlined,
            color: const Color(0xFFF2B91D),
          ),
        ],
      );
    },
  );
}

class _SupportMetric extends StatelessWidget {
  const _SupportMetric({
    required this.width,
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });
  final double width;
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: width,
    height: 104,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: color.withValues(alpha: 0.12),
              child: Icon(icon, color: color),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, maxLines: 2, overflow: TextOverflow.ellipsis),
                  Text(value, style: Theme.of(context).textTheme.headlineSmall),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

class _TicketQueue extends StatelessWidget {
  const _TicketQueue({
    required this.tickets,
    required this.statusFilter,
    required this.assignedOnly,
    required this.onFilter,
    required this.onOpen,
  });
  final List<SupportTicket> tickets;
  final SupportTicketStatus? statusFilter;
  final bool assignedOnly;
  final void Function(SupportTicketStatus?, bool) onFilter;
  final ValueChanged<SupportTicket> onOpen;

  @override
  Widget build(BuildContext context) => _SupportPanel(
    title: 'Recent Tickets',
    child: Column(
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'all', label: Text('All')),
              ButtonSegment(value: 'assigned', label: Text('My Assigned')),
              ButtonSegment(value: 'open', label: Text('Open')),
              ButtonSegment(value: 'resolved', label: Text('Resolved')),
            ],
            selected: {
              assignedOnly
                  ? 'assigned'
                  : statusFilter == SupportTicketStatus.open
                  ? 'open'
                  : statusFilter == SupportTicketStatus.resolved
                  ? 'resolved'
                  : 'all',
            },
            onSelectionChanged: (value) {
              final selected = value.first;
              onFilter(
                selected == 'open'
                    ? SupportTicketStatus.open
                    : selected == 'resolved'
                    ? SupportTicketStatus.resolved
                    : null,
                selected == 'assigned',
              );
            },
          ),
        ),
        const SizedBox(height: 12),
        if (tickets.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 28),
            child: Text('No tickets match this view.'),
          )
        else
          ...tickets
              .take(8)
              .map(
                (ticket) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: CircleAvatar(
                    backgroundColor: _priorityColor(
                      ticket.priority,
                    ).withValues(alpha: 0.12),
                    child: Icon(
                      Icons.support_agent,
                      color: _priorityColor(ticket.priority),
                    ),
                  ),
                  title: Text(ticket.subject),
                  subtitle: Text(
                    '${_category(ticket.category)} • ${ticket.requesterId}',
                  ),
                  trailing: Chip(label: Text(_status(ticket.status))),
                  onTap: () => onOpen(ticket),
                ),
              ),
      ],
    ),
  );
}

class _ActiveChats extends StatelessWidget {
  const _ActiveChats({required this.tickets});
  final List<SupportTicket> tickets;

  @override
  Widget build(BuildContext context) => _SupportPanel(
    title: 'Active Chats',
    child: tickets.isEmpty
        ? const Padding(
            padding: EdgeInsets.symmetric(vertical: 20),
            child: Text('No active conversations.'),
          )
        : Column(
            children: tickets
                .take(5)
                .map(
                  (ticket) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const CircleAvatar(
                      child: Icon(Icons.person_outline),
                    ),
                    title: Text(ticket.requesterId),
                    subtitle: Text(
                      ticket.messages.isEmpty
                          ? ticket.subject
                          : ticket.messages.last.message,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    trailing: const Icon(
                      Icons.circle,
                      size: 9,
                      color: Color(0xFF16B76A),
                    ),
                  ),
                )
                .toList(),
          ),
  );
}

class _KnowledgeBase extends StatelessWidget {
  const _KnowledgeBase({required this.articles});
  final List<KnowledgeArticle> articles;

  @override
  Widget build(BuildContext context) => _SupportPanel(
    title: 'Knowledge Base',
    child: articles.isEmpty
        ? const Padding(
            padding: EdgeInsets.symmetric(vertical: 20),
            child: Text('No published knowledge articles.'),
          )
        : Column(
            children: articles
                .take(5)
                .map(
                  (article) => ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.article_outlined),
                    title: Text(article.title),
                  ),
                )
                .toList(),
          ),
  );
}

class _TicketStatus extends StatelessWidget {
  const _TicketStatus({
    required this.total,
    required this.open,
    required this.assigned,
    required this.waiting,
    required this.resolved,
  });
  final int total;
  final int open;
  final int assigned;
  final int waiting;
  final int resolved;

  @override
  Widget build(BuildContext context) => _SupportPanel(
    title: 'Tickets by Status',
    child: Row(
      children: [
        SizedBox(
          width: 100,
          height: 100,
          child: Stack(
            alignment: Alignment.center,
            children: [
              CircularProgressIndicator(
                value: total == 0 ? 0 : resolved / total,
                strokeWidth: 14,
                backgroundColor: const Color(0xFFE7EBF1),
              ),
              Text('$total\nTotal', textAlign: TextAlign.center),
            ],
          ),
        ),
        const SizedBox(width: 18),
        Expanded(
          child: Column(
            children: [
              _legend('Open', open),
              _legend('My Assigned', assigned),
              _legend('Waiting', waiting),
              _legend('Resolved', resolved),
            ],
          ),
        ),
      ],
    ),
  );
}

class _CategoryChart extends StatelessWidget {
  const _CategoryChart({required this.values});
  final Map<SupportTicketCategory, int> values;

  @override
  Widget build(BuildContext context) {
    final maximum = values.isEmpty
        ? 1
        : values.values.reduce((a, b) => a > b ? a : b);
    return _SupportPanel(
      title: 'Tickets by Category',
      child: values.isEmpty
          ? const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Text('No ticket categories recorded.'),
            )
          : Column(
              children: values.entries
                  .take(6)
                  .map(
                    (entry) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                        children: [
                          SizedBox(
                            width: 150,
                            child: Text(_category(entry.key)),
                          ),
                          Expanded(
                            child: LinearProgressIndicator(
                              value: entry.value / maximum,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Text('${entry.value}'),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
    );
  }
}

class _PerformanceOverview extends StatelessWidget {
  const _PerformanceOverview({required this.report});
  final SupportPerformanceReport report;

  @override
  Widget build(BuildContext context) => _SupportPanel(
    title: 'Performance Overview',
    child: Wrap(
      spacing: 30,
      runSpacing: 16,
      children: [
        _performance('Total Tickets', '${report.totalTickets}'),
        _performance(
          'Resolved Tickets',
          '${report.totalTickets - report.openTickets}',
        ),
        _performance(
          'Response Time',
          _duration(report.averageFirstResponseMinutes),
        ),
        _performance(
          'Resolution Time',
          _duration(report.averageResolutionMinutes),
        ),
        _performance(
          'Satisfaction Score',
          '${report.satisfactionScore.toStringAsFixed(0)}%',
        ),
        _performance('SLA Breaches', '${report.slaBreaches}'),
      ],
    ),
  );
}

class _SupportPanel extends StatelessWidget {
  const _SupportPanel({required this.title, required this.child});
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

Widget _legend(String label, int value) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 5),
  child: Row(
    children: [
      Expanded(child: Text(label)),
      Text('$value'),
    ],
  ),
);

Widget _performance(String label, String value) => SizedBox(
  width: 150,
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label),
      Text(
        value,
        style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
      ),
    ],
  ),
);

String _duration(double minutes) {
  if (minutes <= 0) return '0m';
  final hours = minutes ~/ 60;
  final remainder = minutes.round() % 60;
  return hours == 0 ? '${minutes.round()}m' : '${hours}h ${remainder}m';
}

String _category(SupportTicketCategory category) => category.name
    .replaceAllMapped(
      RegExp(r'([A-Z])'),
      (match) => ' ${match.group(1)!.toLowerCase()}',
    )
    .replaceFirstMapped(
      RegExp(r'^.'),
      (match) => match.group(0)!.toUpperCase(),
    );

String _status(SupportTicketStatus status) => status.name
    .replaceAllMapped(
      RegExp(r'([A-Z])'),
      (match) => ' ${match.group(1)!.toLowerCase()}',
    )
    .replaceFirstMapped(
      RegExp(r'^.'),
      (match) => match.group(0)!.toUpperCase(),
    );

Color _priorityColor(SupportTicketPriority priority) => switch (priority) {
  SupportTicketPriority.low => const Color(0xFF16B76A),
  SupportTicketPriority.normal => const Color(0xFF2878F0),
  SupportTicketPriority.high => const Color(0xFFFF7A21),
  SupportTicketPriority.urgent => const Color(0xFFE83B55),
};
