import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../../provider_analytics/domain/provider_analytics.dart';
import '../../provider_analytics/presentation/provider_analytics_screen.dart';
import '../domain/opportunity.dart';
import '../domain/opportunity_repository.dart';

class ProviderOpportunityScreen extends StatefulWidget {
  const ProviderOpportunityScreen({
    super.key,
    required this.user,
    required this.repository,
    required this.analyticsRepository,
    required this.onSignOut,
  });

  final UserAccount user;
  final OpportunityRepository repository;
  final ProviderAnalyticsRepository analyticsRepository;
  final VoidCallback onSignOut;

  @override
  State<ProviderOpportunityScreen> createState() =>
      _ProviderOpportunityScreenState();
}

class _ProviderOpportunityScreenState extends State<ProviderOpportunityScreen> {
  late Future<
    ({List<Opportunity> opportunities, ProviderAnalyticsSnapshot analytics})
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
    ({List<Opportunity> opportunities, ProviderAnalyticsSnapshot analytics})
  >
  _load() async => (
    opportunities: await widget.repository.getForProvider(widget.user.id),
    analytics: await widget.analyticsRepository.snapshot(widget.user.id),
  );

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
                  _ProviderHeader(
                    showMenu: !desktop,
                    user: widget.user,
                    onCreate: _createOpportunity,
                    onRefresh: () => setState(_reload),
                    onSignOut: widget.onSignOut,
                  ),
                  Expanded(
                    child:
                        FutureBuilder<
                          ({
                            List<Opportunity> opportunities,
                            ProviderAnalyticsSnapshot analytics,
                          })
                        >(
                          future: _data,
                          builder: (context, snapshot) {
                            if (!snapshot.hasData) {
                              return const Center(
                                child: CircularProgressIndicator(),
                              );
                            }
                            return _ProviderDashboard(
                              opportunities: snapshot.data!.opportunities,
                              analytics: snapshot.data!.analytics,
                              onCreate: _createOpportunity,
                              onAnalytics: _openAnalytics,
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

  Widget _navigation() => _ProviderNavigation(
    user: widget.user,
    onCreate: _createOpportunity,
    onAnalytics: _openAnalytics,
    onSignOut: widget.onSignOut,
  );

  Future<void> _openAnalytics() => Navigator.of(context).push<void>(
    MaterialPageRoute(
      builder: (_) => ProviderAnalyticsScreen(
        providerId: widget.user.id,
        repository: widget.analyticsRepository,
      ),
    ),
  );

  Future<void> _createOpportunity() async {
    final created = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (context) => OpportunitySubmissionScreen(
          providerId: widget.user.id,
          providerName: widget.user.fullName,
          repository: widget.repository,
        ),
      ),
    );
    if (created == true) {
      setState(_reload);
    }
  }
}

class _ProviderHeader extends StatelessWidget {
  const _ProviderHeader({
    required this.showMenu,
    required this.user,
    required this.onCreate,
    required this.onRefresh,
    required this.onSignOut,
  });
  final bool showMenu;
  final UserAccount user;
  final VoidCallback onCreate;
  final VoidCallback onRefresh;
  final VoidCallback onSignOut;

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
              Text(
                'Opportunity Provider Dashboard',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const Text(
                'Manage verified opportunities and review engagement.',
              ),
            ],
          ),
        ),
        if (MediaQuery.sizeOf(context).width >= 760)
          const SizedBox(
            width: 320,
            child: TextField(
              readOnly: true,
              decoration: InputDecoration(
                isDense: true,
                prefixIcon: Icon(Icons.search),
                hintText: 'Search opportunities or statistics...',
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
        if (MediaQuery.sizeOf(context).width >= 620)
          FilledButton.icon(
            onPressed: onCreate,
            icon: const Icon(Icons.add),
            label: const Text('Create opportunity'),
          ),
        PopupMenuButton<String>(
          tooltip: 'Provider account',
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

class _ProviderNavigation extends StatelessWidget {
  const _ProviderNavigation({
    required this.user,
    required this.onCreate,
    required this.onAnalytics,
    required this.onSignOut,
  });
  final UserAccount user;
  final VoidCallback onCreate;
  final VoidCallback onAnalytics;
  final VoidCallback onSignOut;

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
                        'Opportunities Without Borders',
                        style: TextStyle(color: Color(0xFFB8C7DC), fontSize: 9),
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
                _providerNav(
                  Icons.dashboard_outlined,
                  'Dashboard',
                  () {},
                  true,
                ),
                _providerSection('OPPORTUNITIES'),
                _providerNav(
                  Icons.inventory_2_outlined,
                  'My Opportunities',
                  () {},
                ),
                _providerNav(
                  Icons.add_circle_outline,
                  'Create Opportunity',
                  onCreate,
                ),
                _providerNav(Icons.drafts_outlined, 'Drafts', () {}),
                _providerNav(Icons.send_outlined, 'Submissions', () {}),
                _providerNav(Icons.verified_outlined, 'Published', () {}),
                _providerNav(Icons.event_busy_outlined, 'Expired', () {}),
                _providerNav(Icons.archive_outlined, 'Archived', () {}),
                _providerSection('APPLICATIONS'),
                _providerNav(
                  Icons.groups_outlined,
                  'All Applications',
                  onAnalytics,
                ),
                _providerNav(Icons.star_outline, 'Shortlisted', onAnalytics),
                _providerNav(
                  Icons.emoji_events_outlined,
                  'Selected',
                  onAnalytics,
                ),
                _providerNav(
                  Icons.person_off_outlined,
                  'Rejected',
                  onAnalytics,
                ),
                _providerSection('ANALYTICS'),
                _providerNav(Icons.analytics_outlined, 'Overview', onAnalytics),
                _providerNav(
                  Icons.description_outlined,
                  'Reports',
                  onAnalytics,
                ),
                _providerNav(Icons.download_outlined, 'Downloads', onAnalytics),
                _providerSection('SETTINGS'),
                _providerNav(
                  Icons.business_outlined,
                  'Organization Profile',
                  () {},
                ),
                _providerNav(Icons.group_outlined, 'Team Members', () {}),
                _providerNav(
                  Icons.settings_outlined,
                  'Account Settings',
                  () {},
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
                        'Provider Account • Verified',
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
        ],
      ),
    ),
  );
}

class _ProviderDashboard extends StatelessWidget {
  const _ProviderDashboard({
    required this.opportunities,
    required this.analytics,
    required this.onCreate,
    required this.onAnalytics,
  });
  final List<Opportunity> opportunities;
  final ProviderAnalyticsSnapshot analytics;
  final VoidCallback onCreate;
  final VoidCallback onAnalytics;

  @override
  Widget build(BuildContext context) {
    int status(VerificationStatus value) =>
        opportunities.where((item) => item.verificationStatus == value).length;
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1300),
            child: Column(
              children: [
                _ProviderMetrics(
                  total: opportunities.length,
                  published: status(VerificationStatus.verified),
                  applications: analytics.applicationClicks,
                  views: analytics.views,
                  saves: analytics.saves,
                ),
                const SizedBox(height: 16),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final width = constraints.maxWidth >= 820
                        ? (constraints.maxWidth - 16) / 2
                        : constraints.maxWidth;
                    return Wrap(
                      spacing: 16,
                      runSpacing: 16,
                      children: [
                        SizedBox(
                          width: width,
                          child: _EngagementOverview(analytics: analytics),
                        ),
                        SizedBox(
                          width: width,
                          child: _OpportunityStatus(
                            opportunities: opportunities,
                          ),
                        ),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 16),
                _ProviderOpportunityTable(
                  opportunities: opportunities,
                  onCreate: onCreate,
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
                          child: _ProviderQuickActions(
                            onCreate: onCreate,
                            onAnalytics: onAnalytics,
                          ),
                        ),
                        SizedBox(width: width, child: const _ProviderTips()),
                        SizedBox(
                          width: width,
                          child: const _ProviderResources(),
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

class _ProviderMetrics extends StatelessWidget {
  const _ProviderMetrics({
    required this.total,
    required this.published,
    required this.applications,
    required this.views,
    required this.saves,
  });
  final int total;
  final int published;
  final int applications;
  final int views;
  final int saves;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final columns = constraints.maxWidth >= 1050
          ? 5
          : constraints.maxWidth >= 650
          ? 3
          : 2;
      final width = (constraints.maxWidth - (columns - 1) * 12) / columns;
      final values = [
        (
          'Total Opportunities',
          total,
          Icons.inventory_2_outlined,
          const Color(0xFF7047EB),
        ),
        (
          'Published Opportunities',
          published,
          Icons.verified_outlined,
          const Color(0xFF16B76A),
        ),
        (
          'Application Clicks',
          applications,
          Icons.groups_outlined,
          const Color(0xFF2878F0),
        ),
        (
          'Opportunity Views',
          views,
          Icons.visibility_outlined,
          const Color(0xFFFF7A21),
        ),
        ('Saved', saves, Icons.star_outline, const Color(0xFFF2B91D)),
      ];
      return Wrap(
        spacing: 12,
        runSpacing: 12,
        children: values
            .map(
              (item) => SizedBox(
                width: width,
                height: 124,
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        CircleAvatar(
                          backgroundColor: item.$4.withValues(alpha: 0.12),
                          child: Icon(item.$3, color: item.$4),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(item.$1, maxLines: 2),
                              Text(
                                '${item.$2}',
                                style: Theme.of(context)
                                    .textTheme
                                    .headlineSmall,
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

class _EngagementOverview extends StatelessWidget {
  const _EngagementOverview({required this.analytics});
  final ProviderAnalyticsSnapshot analytics;

  @override
  Widget build(BuildContext context) => _ProviderPanel(
    title: 'Applications Overview',
    child: SizedBox(
      height: 155,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          _bar('Views', analytics.views, const Color(0xFF2878F0)),
          _bar('Saves', analytics.saves, const Color(0xFF16B76A)),
          _bar('Clicks', analytics.applicationClicks, const Color(0xFF7047EB)),
        ],
      ),
    ),
  );
}

class _OpportunityStatus extends StatelessWidget {
  const _OpportunityStatus({required this.opportunities});
  final List<Opportunity> opportunities;

  @override
  Widget build(BuildContext context) {
    int count(VerificationStatus value) =>
        opportunities.where((item) => item.verificationStatus == value).length;
    return _ProviderPanel(
      title: 'Opportunities by Status',
      child: Row(
        children: [
          SizedBox(
            width: 115,
            height: 115,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CircularProgressIndicator(
                  value: opportunities.isEmpty
                      ? 0
                      : count(VerificationStatus.verified) /
                            opportunities.length,
                  strokeWidth: 14,
                  backgroundColor: const Color(0xFFE7EBF1),
                  color: const Color(0xFF16B76A),
                ),
                Text(
                  '${opportunities.length}\nTotal',
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
          const SizedBox(width: 18),
          Expanded(
            child: Column(
              children: [
                _providerValue('Published', count(VerificationStatus.verified)),
                _providerValue(
                  'Under Review',
                  count(VerificationStatus.pending),
                ),
                _providerValue('Expired', count(VerificationStatus.expired)),
                _providerValue('Archived', count(VerificationStatus.archived)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProviderOpportunityTable extends StatelessWidget {
  const _ProviderOpportunityTable({
    required this.opportunities,
    required this.onCreate,
  });
  final List<Opportunity> opportunities;
  final VoidCallback onCreate;

  @override
  Widget build(BuildContext context) => _ProviderPanel(
    title: 'My Opportunities',
    child: opportunities.isEmpty
        ? Padding(
            padding: const EdgeInsets.symmetric(vertical: 28),
            child: Center(
              child: Column(
                children: [
                  const Text('No opportunities submitted yet.'),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: onCreate,
                    icon: const Icon(Icons.add),
                    label: const Text('Create opportunity'),
                  ),
                ],
              ),
            ),
          )
        : Column(
            children: opportunities
                .take(7)
                .map(
                  (item) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const CircleAvatar(
                      child: Icon(Icons.school_outlined),
                    ),
                    title: Text(item.title),
                    subtitle: Text('${item.hostCountry} • ${item.typeLabel}'),
                    trailing: Chip(label: Text(item.verificationLabel)),
                  ),
                )
                .toList(),
          ),
  );
}

class _ProviderQuickActions extends StatelessWidget {
  const _ProviderQuickActions({
    required this.onCreate,
    required this.onAnalytics,
  });
  final VoidCallback onCreate;
  final VoidCallback onAnalytics;

  @override
  Widget build(BuildContext context) => _ProviderPanel(
    title: 'Quick Actions',
    child: Column(
      children: [
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.add_circle_outline),
          title: const Text('Create opportunity'),
          onTap: onCreate,
        ),
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.analytics_outlined),
          title: const Text('View analytics'),
          onTap: onAnalytics,
        ),
      ],
    ),
  );
}

class _ProviderTips extends StatelessWidget {
  const _ProviderTips();

  @override
  Widget build(BuildContext context) => const _ProviderPanel(
    title: 'Tips for Providers',
    child: ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(Icons.star_outline, color: Color(0xFF7047EB)),
      title: Text('Keep organization and source information current.'),
      subtitle: Text(
        'Complete every opportunity field to improve applicant trust.',
      ),
    ),
  );
}

class _ProviderResources extends StatelessWidget {
  const _ProviderResources();

  @override
  Widget build(BuildContext context) => const _ProviderPanel(
    title: 'Provider Resources',
    child: Column(
      children: [
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.article_outlined),
          title: Text('Provider Guidelines'),
        ),
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.verified_user_outlined),
          title: Text('Best Practices'),
        ),
        ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.help_outline),
          title: Text('Help Center'),
        ),
      ],
    ),
  );
}

class _ProviderPanel extends StatelessWidget {
  const _ProviderPanel({required this.title, required this.child});
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

Widget _providerNav(
  IconData icon,
  String label,
  VoidCallback onTap, [
  bool selected = false,
]) => Padding(
  padding: const EdgeInsets.only(bottom: 2),
  child: ListTile(
    dense: true,
    selected: selected,
    selectedTileColor: const Color(0xFF5238E8),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(7)),
    leading: Icon(icon, color: Colors.white, size: 19),
    title: Text(
      label,
      style: const TextStyle(color: Colors.white, fontSize: 13),
    ),
    onTap: onTap,
  ),
);

Widget _providerSection(String label) => Padding(
  padding: const EdgeInsets.fromLTRB(12, 17, 12, 6),
  child: Text(
    label,
    style: const TextStyle(color: Color(0xFF8FA6C3), fontSize: 10),
  ),
);

Widget _providerValue(String label, int value) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 7),
  child: Row(
    children: [
      Expanded(child: Text(label)),
      Text('$value'),
    ],
  ),
);

Widget _bar(String label, int value, Color color) {
  final height = (value <= 0 ? 20 : 40 + value.clamp(0, 100)).toDouble();
  return Expanded(
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Text('$value'),
          const SizedBox(height: 5),
          Container(
            height: height,
            decoration: BoxDecoration(
              color: color,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(4),
              ),
            ),
          ),
          const SizedBox(height: 5),
          Text(label),
        ],
      ),
    ),
  );
}

class OpportunitySubmissionScreen extends StatefulWidget {
  const OpportunitySubmissionScreen({
    super.key,
    required this.providerId,
    required this.providerName,
    required this.repository,
  });

  final String providerId;
  final String providerName;
  final OpportunityRepository repository;

  @override
  State<OpportunitySubmissionScreen> createState() =>
      _OpportunitySubmissionScreenState();
}

class _OpportunitySubmissionScreenState
    extends State<OpportunitySubmissionScreen> {
  final _formKey = GlobalKey<FormState>();
  final Map<String, TextEditingController> _fields = {};
  OpportunityType _type = OpportunityType.scholarship;
  FundingType _funding = FundingType.fullyFunded;
  DeliveryFormat _delivery = DeliveryFormat.physical;
  bool _submitting = false;

  TextEditingController _controller(String key) =>
      _fields.putIfAbsent(key, () => TextEditingController());

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Submit opportunity')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 760),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _section(context, 'Core information'),
                    _requiredField('title', 'Opportunity title'),
                    _requiredField('institution', 'Host institution'),
                    _requiredField('country', 'Host country'),
                    _enumField<OpportunityType>(
                      'Opportunity type',
                      _type,
                      OpportunityType.values,
                      (value) => setState(() => _type = value),
                    ),
                    _enumField<FundingType>(
                      'Funding type',
                      _funding,
                      FundingType.values,
                      (value) => setState(() => _funding = value),
                    ),
                    _enumField<DeliveryFormat>(
                      'Delivery format',
                      _delivery,
                      DeliveryFormat.values,
                      (value) => setState(() => _delivery = value),
                    ),
                    _requiredField('summary', 'Summary', maxLines: 4),
                    const SizedBox(height: 20),
                    _section(context, 'Eligibility and benefits'),
                    _listField('nationalities', 'Eligible nationalities'),
                    _listField('levels', 'Study levels'),
                    _listField('fields', 'Fields of study'),
                    _listField('benefits', 'Benefits'),
                    _listField('eligibility', 'Eligibility requirements'),
                    _listField('documents', 'Required documents'),
                    _listField('languages', 'Language requirements'),
                    _requiredField(
                      'minimumAge',
                      'Minimum age (optional)',
                      isRequired: false,
                      keyboardType: TextInputType.number,
                    ),
                    _requiredField(
                      'maximumAge',
                      'Maximum age (optional)',
                      isRequired: false,
                      keyboardType: TextInputType.number,
                    ),
                    _requiredField(
                      'experience',
                      'Required work experience in years (optional)',
                      isRequired: false,
                      keyboardType: TextInputType.number,
                    ),
                    const SizedBox(height: 20),
                    _section(context, 'Application information'),
                    _dateField('openDate', 'Application opening date'),
                    _dateField('deadline', 'Application deadline'),
                    _requiredField(
                      'applicationUrl',
                      'Official application URL',
                    ),
                    _requiredField('sourceUrl', 'Official source URL'),
                    _requiredField(
                      'fee',
                      'Application fee',
                      keyboardType: TextInputType.number,
                    ),
                    _requiredField(
                      'positions',
                      'Available positions (optional)',
                      isRequired: false,
                      keyboardType: TextInputType.number,
                    ),
                    _listField('procedure', 'Application procedure'),
                    _requiredField('contact', 'Contact information'),
                    const SizedBox(height: 28),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        key: const Key('submit-opportunity'),
                        onPressed: _submitting ? null : _submit,
                        icon: const Icon(Icons.send_outlined),
                        label: Text(
                          _submitting
                              ? 'Submitting...'
                              : 'Submit for verification',
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _section(BuildContext context, String title) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Text(title, style: Theme.of(context).textTheme.headlineSmall),
  );

  Widget _requiredField(
    String key,
    String label, {
    bool isRequired = true,
    int maxLines = 1,
    TextInputType? keyboardType,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: TextFormField(
      controller: _controller(key),
      maxLines: maxLines,
      keyboardType: keyboardType,
      decoration: InputDecoration(labelText: label),
      validator: isRequired
          ? (value) => value == null || value.trim().isEmpty
                ? '$label is required.'
                : null
          : null,
    ),
  );

  Widget _listField(String key, String label) => _requiredField(key, label);

  Widget _dateField(String key, String label) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: TextFormField(
      controller: _controller(key),
      readOnly: true,
      decoration: InputDecoration(
        labelText: label,
        helperText: 'Select a date',
        suffixIcon: const Icon(Icons.calendar_today_outlined),
      ),
      validator: (value) =>
          value == null || value.isEmpty ? '$label is required.' : null,
      onTap: () async {
        final date = await showDatePicker(
          context: context,
          firstDate: DateTime.now().subtract(const Duration(days: 365)),
          lastDate: DateTime.now().add(const Duration(days: 3650)),
          initialDate: DateTime.now(),
        );
        if (date != null) {
          _controller(key).text = _dateText(date);
        }
      },
    ),
  );

  Widget _enumField<T extends Enum>(
    String label,
    T value,
    List<T> values,
    ValueChanged<T> onChanged,
  ) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: DropdownButtonFormField<T>(
      initialValue: value,
      decoration: InputDecoration(labelText: label),
      items: values
          .map(
            (item) => DropdownMenuItem(
              value: item,
              child: Text(_enumLabel(item.name)),
            ),
          )
          .toList(),
      onChanged: (item) {
        if (item != null) onChanged(item);
      },
    ),
  );

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final openDate = DateTime.parse(_controller('openDate').text);
    final deadline = DateTime.parse(_controller('deadline').text);
    if (!deadline.isAfter(openDate)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('The deadline must be after the opening date.'),
        ),
      );
      return;
    }
    setState(() => _submitting = true);
    await widget.repository.submit(
      providerId: widget.providerId,
      opportunity: Opportunity(
        id: 'provider-${DateTime.now().microsecondsSinceEpoch}',
        title: _value('title'),
        provider: widget.providerName,
        hostInstitution: _value('institution'),
        hostCountry: _value('country'),
        type: _type,
        funding: _funding,
        deadline: deadline,
        applicationOpenDate: openDate,
        verificationStatus: VerificationStatus.pending,
        lastVerifiedAt: null,
        officialSourceUrl: _value('sourceUrl'),
        applicationUrl: _value('applicationUrl'),
        eligibleNationalities: _list('nationalities'),
        studyLevels: _list('levels'),
        fieldsOfStudy: _list('fields'),
        summary: _value('summary'),
        benefits: _list('benefits'),
        eligibilityRequirements: _list('eligibility'),
        requiredDocuments: _list('documents'),
        applicationProcedure: _list('procedure'),
        languageRequirements: _list('languages'),
        minimumAge: int.tryParse(_value('minimumAge')),
        maximumAge: int.tryParse(_value('maximumAge')),
        workExperienceYearsRequired: double.tryParse(_value('experience')),
        contactInformation: _value('contact'),
        availablePositions: int.tryParse(_value('positions')),
        deliveryFormat: _delivery,
        applicationFee: double.tryParse(_value('fee')),
      ),
    );
    if (!mounted) return;
    Navigator.of(context).pop(true);
  }

  String _value(String key) => _controller(key).text.trim();

  List<String> _list(String key) =>
      _value(key)
          .split(',')
          .map((value) => value.trim())
          .where((value) => value.isNotEmpty)
          .toList();

  static String _dateText(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';

  static String _enumLabel(String value) => value.replaceAllMapped(
    RegExp(r'([A-Z])'),
    (match) => ' ${match.group(1)!.toLowerCase()}',
  );
}
