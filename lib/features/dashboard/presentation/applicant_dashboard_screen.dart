import 'package:flutter/material.dart';

import '../../applications/domain/application_record.dart';
import '../../applications/domain/application_repository.dart';
import '../../authentication/domain/user_account.dart';
import '../../notifications/domain/notification.dart';
import '../../notifications/domain/notification_repository.dart';
import '../../opportunities/domain/opportunity.dart';
import '../../opportunities/domain/opportunity_repository.dart';
import '../../profiles/domain/applicant_profile.dart';
import '../../profiles/domain/applicant_profile_repository.dart';

class ApplicantDashboardScreen extends StatefulWidget {
  const ApplicantDashboardScreen({
    super.key,
    required this.user,
    required this.opportunityRepository,
    required this.profileRepository,
    required this.applicationRepository,
    required this.notificationRepository,
    required this.opportunityScreen,
    required this.openApplications,
    required this.openSaved,
    required this.openNotifications,
    required this.openProfile,
    required this.openCalendar,
    required this.openDocuments,
    required this.openSettings,
    required this.openPremium,
    required this.onSignOut,
  });

  final UserAccount user;
  final OpportunityRepository opportunityRepository;
  final ApplicantProfileRepository profileRepository;
  final ApplicationRepository applicationRepository;
  final NotificationRepository notificationRepository;
  final Widget opportunityScreen;
  final VoidCallback openApplications;
  final VoidCallback openSaved;
  final VoidCallback openNotifications;
  final VoidCallback openProfile;
  final VoidCallback openCalendar;
  final VoidCallback openDocuments;
  final VoidCallback openSettings;
  final VoidCallback openPremium;
  final VoidCallback onSignOut;

  @override
  State<ApplicantDashboardScreen> createState() =>
      _ApplicantDashboardScreenState();
}

class _ApplicantDashboardScreenState extends State<ApplicantDashboardScreen> {
  late Future<_DashboardData> _data;
  int _unreadNotifications = 0;

  @override
  void initState() {
    super.initState();
    _startLoad();
  }

  void _startLoad() {
    _data = _load();
    _data.then((data) {
      if (mounted)
        setState(() => _unreadNotifications = data.unreadNotifications);
    });
  }

  Future<_DashboardData> _load() async {
    final results = await Future.wait([
      widget.opportunityRepository.getPublished(),
      widget.applicationRepository.getForUser(widget.user.id),
      widget.notificationRepository.getForUser(widget.user.id),
      widget.profileRepository.getForUser(widget.user.id),
    ]);
    return _DashboardData(
      opportunities: results[0] as List<Opportunity>,
      applications: results[1] as List<ApplicationRecord>,
      notifications: results[2] as List<ScholarSphereNotification>,
      profile:
          results[3] as ApplicantProfile? ??
          ApplicantProfile.empty(widget.user),
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
            if (desktop) SizedBox(width: 260, child: _navigation()),
            Expanded(
              child: Column(
                children: [
                  _TopBar(
                    showMenu: !desktop,
                    user: widget.user,
                    unreadNotifications: _unreadNotifications,
                    onSearch: _openOpportunities,
                    onNotifications: widget.openNotifications,
                    onProfile: widget.openProfile,
                    onSignOut: widget.onSignOut,
                  ),
                  Expanded(
                    child: FutureBuilder<_DashboardData>(
                      future: _data,
                      builder: (context, snapshot) {
                        if (snapshot.hasError) {
                          return _DashboardError(
                            onRetry: () => setState(_startLoad),
                          );
                        }
                        if (!snapshot.hasData) {
                          return Center(
                            child: Semantics(
                              label: 'Loading dashboard',
                              child: const SizedBox(
                                width: 36,
                                height: 36,
                                child: CircularProgressIndicator(),
                              ),
                            ),
                          );
                        }
                        return _DashboardBody(
                          data: snapshot.data!,
                          user: widget.user,
                          openOpportunities: _openOpportunities,
                          openApplications: widget.openApplications,
                          openSaved: widget.openSaved,
                          openNotifications: widget.openNotifications,
                          openCalendar: widget.openCalendar,
                          openProfile: widget.openProfile,
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

  Widget _navigation({bool compact = false}) => _SideNavigation(
    user: widget.user,
    compact: compact,
    openDashboard: () {
      if (compact) Navigator.pop(context);
    },
    openOpportunities: _openOpportunities,
    openRecommendations: _openOpportunities,
    openApplications: widget.openApplications,
    openSaved: widget.openSaved,
    openNotifications: widget.openNotifications,
    openDocuments: widget.openDocuments,
    openCalendar: widget.openCalendar,
    openProfile: widget.openProfile,
    openSettings: widget.openSettings,
    openPremium: widget.openPremium,
  );

  void _openOpportunities() {
    Navigator.of(
      context,
    ).push(MaterialPageRoute<void>(builder: (_) => widget.opportunityScreen));
  }
}

class _DashboardError extends StatelessWidget {
  const _DashboardError({required this.onRetry});
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
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
            "We couldn't load your dashboard.",
            style: TextStyle(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          const Text('Check your connection and try again.'),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
      ),
    ),
  );
}

class _DashboardData {
  const _DashboardData({
    required this.opportunities,
    required this.applications,
    required this.notifications,
    required this.profile,
  });
  final List<Opportunity> opportunities;
  final List<ApplicationRecord> applications;
  final List<ScholarSphereNotification> notifications;
  final ApplicantProfile profile;

  List<ApplicationRecord> get saved => applications
      .where(
        (item) =>
            item.stage == ApplicationStage.saved ||
            item.stage == ApplicationStage.interested,
      )
      .toList();

  int get activeApplications => applications.length - saved.length;

  int get unreadNotifications =>
      notifications.where((item) => !item.isRead).length;

  int get closingSoon {
    final now = DateTime.now();
    return opportunities
        .where(
          (item) =>
              item.deadline.isAfter(now) &&
              item.deadline.difference(now).inDays <= 30,
        )
        .length;
  }

  int get profileStrength {
    final values = <bool>[
      profile.nationality.isNotEmpty,
      profile.countryOfResidence.isNotEmpty,
      profile.dateOfBirth != null,
      profile.highestQualification.isNotEmpty,
      profile.degreeField.isNotEmpty,
      profile.graduationYear != null,
      profile.preferredStudyLevels.isNotEmpty,
      profile.preferredCountries.isNotEmpty,
      profile.areasOfInterest.isNotEmpty,
      profile.documents.isNotEmpty,
    ];
    return (values.where((value) => value).length * 100 / values.length)
        .round();
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.showMenu,
    required this.user,
    required this.unreadNotifications,
    required this.onSearch,
    required this.onNotifications,
    required this.onProfile,
    required this.onSignOut,
  });
  final bool showMenu;
  final UserAccount user;
  final int unreadNotifications;
  final VoidCallback onSearch;
  final VoidCallback onNotifications;
  final VoidCallback onProfile;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return Container(
      height: 72,
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
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 680),
              child: TextField(
                key: const Key('dashboard-search'),
                readOnly: true,
                onTap: onSearch,
                decoration: const InputDecoration(
                  isDense: true,
                  prefixIcon: Icon(Icons.search),
                  hintText:
                      'Search scholarships, fellowships, webinars, summits and more...',
                ),
              ),
            ),
          ),
          const Spacer(),
          // The tooltip string doubles as the accessible name for IconButton,
          // so making it contextual ("3 unread notifications") satisfies the
          // "announce a meaningful phrase, not a bare number" a11y guidance
          // without a second, competing Semantics node around the badge.
          Badge.count(
            count: unreadNotifications,
            isLabelVisible: unreadNotifications > 0,
            child: IconButton(
              tooltip: unreadNotifications > 0
                  ? '$unreadNotifications unread notifications'
                  : 'Notifications',
              onPressed: onNotifications,
              icon: const Icon(Icons.notifications_none),
            ),
          ),
          PopupMenuButton<String>(
            tooltip: 'Account',
            onSelected: (value) {
              if (value == 'profile') onProfile();
              if (value == 'sign-out') onSignOut();
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'profile', child: Text('Edit profile')),
              PopupMenuItem(value: 'sign-out', child: Text('Sign out')),
            ],
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 18,
                    backgroundColor: primary.withValues(alpha: 0.14),
                    foregroundColor: primary,
                    child: Text(user.fullName.substring(0, 1)),
                  ),
                  const SizedBox(width: 9),
                  if (MediaQuery.sizeOf(context).width >= 700)
                    Text('Hi, ${user.fullName.split(' ').first}'),
                  const Icon(Icons.keyboard_arrow_down, size: 18),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SideNavigation extends StatelessWidget {
  const _SideNavigation({
    required this.user,
    required this.compact,
    required this.openDashboard,
    required this.openOpportunities,
    required this.openRecommendations,
    required this.openApplications,
    required this.openSaved,
    required this.openNotifications,
    required this.openDocuments,
    required this.openCalendar,
    required this.openProfile,
    required this.openSettings,
    required this.openPremium,
  });
  final UserAccount user;
  final bool compact;
  final VoidCallback openDashboard;
  final VoidCallback openOpportunities;
  final VoidCallback openRecommendations;
  final VoidCallback openApplications;
  final VoidCallback openSaved;
  final VoidCallback openNotifications;
  final VoidCallback openDocuments;
  final VoidCallback openCalendar;
  final VoidCallback openProfile;
  final VoidCallback openSettings;
  final VoidCallback openPremium;

  @override
  Widget build(BuildContext context) => Material(
    color: const Color(0xFF14213D), // brand ink, matches the login side panel
    child: SafeArea(
      child: Column(
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(22, 18, 16, 22),
            child: Row(
              children: [
                Icon(Icons.school_outlined, color: Colors.white, size: 34),
                SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'ScholarSphere',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
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
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                _nav(
                  Icons.dashboard_outlined,
                  'Dashboard',
                  openDashboard,
                  true,
                ),
                _nav(Icons.workspace_premium_outlined, 'Premium', openPremium),
                _nav(
                  Icons.explore_outlined,
                  'Opportunities',
                  openOpportunities,
                ),
                _nav(
                  Icons.star_outline,
                  'Recommendations',
                  openRecommendations,
                ),
                _nav(
                  Icons.assignment_outlined,
                  'Application Tracker',
                  openApplications,
                ),
                _nav(Icons.bookmark_outline, 'Saved Opportunities', openSaved),
                _nav(
                  Icons.notifications_none,
                  'Notifications',
                  openNotifications,
                ),
                _nav(Icons.folder_outlined, 'Documents', openDocuments),
                _nav(Icons.calendar_month_outlined, 'Calendar', openCalendar),
                _nav(Icons.person_outline, 'Profile', openProfile),
                _nav(
                  Icons.fact_check_outlined,
                  'Eligibility Checker',
                  openOpportunities,
                ),
                _nav(
                  Icons.headset_mic_outlined,
                  'Help & Support',
                  openSettings,
                ),
                _nav(Icons.settings_outlined, 'Settings', openSettings),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              user.email,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Color(0xFFB8C7DC), fontSize: 11),
            ),
          ),
        ],
      ),
    ),
  );

  Widget _nav(
    IconData icon,
    String label,
    VoidCallback onTap, [
    bool selected = false,
  ]) => Padding(
    padding: const EdgeInsets.only(bottom: 3),
    child: ListTile(
      selected: selected,
      selectedTileColor: const Color(0xFF007C72), // brand teal (primary)
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(7)),
      leading: Icon(icon, color: Colors.white, size: 21),
      title: Text(
        label,
        style: const TextStyle(color: Colors.white, fontSize: 14),
      ),
      onTap: onTap,
    ),
  );
}

class _DashboardBody extends StatelessWidget {
  const _DashboardBody({
    required this.data,
    required this.user,
    required this.openOpportunities,
    required this.openApplications,
    required this.openSaved,
    required this.openNotifications,
    required this.openCalendar,
    required this.openProfile,
  });
  final _DashboardData data;
  final UserAccount user;
  final VoidCallback openOpportunities;
  final VoidCallback openApplications;
  final VoidCallback openSaved;
  final VoidCallback openNotifications;
  final VoidCallback openCalendar;
  final VoidCallback openProfile;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final twoColumns = constraints.maxWidth >= 840;
      final main = Column(
        children: [
          _Welcome(data: data, user: user, openProfile: openProfile),
          const SizedBox(height: 16),
          _Metrics(
            data: data,
            openOpportunities: openOpportunities,
            openSaved: openSaved,
            openApplications: openApplications,
          ),
          const SizedBox(height: 16),
          _Recommendations(
            opportunities: data.opportunities,
            onViewAll: openOpportunities,
          ),
          const SizedBox(height: 16),
          _SavedList(records: data.saved, onViewAll: openSaved),
        ],
      );
      final side = Column(
        children: [
          _Deadlines(
            opportunities: data.opportunities,
            onCalendar: openCalendar,
          ),
          const SizedBox(height: 16),
          _ApplicationSummary(
            records: data.applications,
            onOpen: openApplications,
          ),
          const SizedBox(height: 16),
          _Notifications(
            notifications: data.notifications,
            onOpen: openNotifications,
          ),
        ],
      );
      return SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1280),
            child: twoColumns
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 3, child: main),
                      const SizedBox(width: 16),
                      Expanded(flex: 2, child: side),
                    ],
                  )
                : Column(children: [main, const SizedBox(height: 16), side]),
          ),
        ),
      );
    },
  );
}

class _Welcome extends StatelessWidget {
  const _Welcome({
    required this.data,
    required this.user,
    required this.openProfile,
  });
  final _DashboardData data;
  final UserAccount user;
  final VoidCallback openProfile;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: const Color(0xFFE6F4F2) /* brand teal tint */,
      borderRadius: BorderRadius.circular(8),
    ),
    child: Row(
      children: [
        CircleAvatar(
          radius: 42,
          backgroundColor: const Color(0xFF007C72), // brand teal (primary)
          child: Text(
            user.fullName.split(' ').take(2).map((part) => part[0]).join(),
            style: const TextStyle(color: Colors.white, fontSize: 24),
          ),
        ),
        const SizedBox(width: 20),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Welcome back,'),
              Text(
                user.fullName,
                style: Theme.of(context).textTheme.headlineLarge,
              ),
              const Text('Your next opportunity starts with one good match.'),
            ],
          ),
        ),
        if (MediaQuery.sizeOf(context).width >= 640)
          TextButton(
            onPressed: openProfile,
            child: Text('${data.profileStrength}% profile'),
          ),
      ],
    ),
  );
}

class _Metrics extends StatelessWidget {
  const _Metrics({
    required this.data,
    required this.openOpportunities,
    required this.openSaved,
    required this.openApplications,
  });
  final _DashboardData data;
  final VoidCallback openOpportunities;
  final VoidCallback openSaved;
  final VoidCallback openApplications;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth >= 620
              ? (constraints.maxWidth - 36) / 4
              : (constraints.maxWidth - 12) / 2;
          final scheme = Theme.of(context).colorScheme;
          return Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _Metric(
                width: width,
                icon: Icons.school_outlined,
                color: scheme.primary,
                value: data.opportunities.length,
                label: 'Matches',
                onTap: openOpportunities,
              ),
              _Metric(
                width: width,
                icon: Icons.bookmark_outline,
                color: scheme.secondary,
                value: data.saved.length,
                label: 'Saved',
                onTap: openSaved,
              ),
              _Metric(
                width: width,
                icon: Icons.send_outlined,
                color: const Color(0xFF14213D), // brand ink
                value: data.activeApplications,
                label: 'Applications',
                onTap: openApplications,
              ),
              _Metric(
                width: width,
                icon: Icons.schedule,
                color:
                    scheme.error, // urgency — matches the "deadline" semantic
                value: data.closingSoon,
                label: 'Closing soon',
                onTap: openOpportunities,
              ),
            ],
          );
        },
      ),
    ),
  );
}

class _Metric extends StatelessWidget {
  const _Metric({
    required this.width,
    required this.icon,
    required this.color,
    required this.value,
    required this.label,
    required this.onTap,
  });
  final double width;
  final IconData icon;
  final Color color;
  final int value;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: width,
    height: 102,
    child: InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: DecoratedBox(
        decoration: BoxDecoration(
          border: Border.all(color: const Color(0xFFE7EBF1)),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
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
                    Text(
                      '$value',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    Text(label, maxLines: 1, overflow: TextOverflow.ellipsis),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _Recommendations extends StatelessWidget {
  const _Recommendations({
    required this.opportunities,
    required this.onViewAll,
  });
  final List<Opportunity> opportunities;
  final VoidCallback onViewAll;

  @override
  Widget build(BuildContext context) => _Panel(
    title: 'Recommended for You',
    onViewAll: onViewAll,
    child: SizedBox(
      height: 235,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: opportunities.take(4).length,
        separatorBuilder: (_, _) => const SizedBox(width: 10),
        itemBuilder: (_, index) {
          final item = opportunities[index];
          return SizedBox(
            width: 205,
            child: Card(
              child: InkWell(
                onTap: onViewAll,
                child: Padding(
                  padding: const EdgeInsets.all(13),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.fundingLabel,
                        style: const TextStyle(
                          color: Color(0xFF007C72),
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        item.title,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        item.provider,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const Spacer(),
                      Text(item.hostCountry),
                      const SizedBox(height: 8),
                      Text('Deadline: ${_date(item.deadline)}'),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
    ),
  );
}

class _Deadlines extends StatelessWidget {
  const _Deadlines({required this.opportunities, required this.onCalendar});
  final List<Opportunity> opportunities;
  final VoidCallback onCalendar;

  @override
  Widget build(BuildContext context) {
    final sorted = [...opportunities]
      ..sort((a, b) => a.deadline.compareTo(b.deadline));
    return _Panel(
      title: 'Upcoming Deadlines',
      onViewAll: onCalendar,
      child: Column(
        children: [
          ...sorted
              .take(3)
              .map(
                (item) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const CircleAvatar(
                    backgroundColor: Color(0xFFE6F4F2) /* brand teal tint */,
                    child: Icon(Icons.school_outlined, size: 19),
                  ),
                  title: Text(
                    item.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  subtitle: Text(item.provider),
                  trailing: Text(_date(item.deadline)),
                ),
              ),
          SizedBox(
            width: double.infinity,
            child: TextButton.icon(
              onPressed: onCalendar,
              icon: const Icon(Icons.calendar_today_outlined),
              label: const Text('Go to Calendar'),
            ),
          ),
        ],
      ),
    );
  }
}

class _ApplicationSummary extends StatelessWidget {
  const _ApplicationSummary({required this.records, required this.onOpen});
  final List<ApplicationRecord> records;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final submitted = records
        .where((item) => item.stage == ApplicationStage.applicationSubmitted)
        .length;
    return _Panel(
      title: 'Application Tracker',
      onViewAll: onOpen,
      child: Column(
        children: [
          Row(
            children: [
              SizedBox(
                width: 100,
                height: 100,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    CircularProgressIndicator(
                      value: records.isEmpty ? 0 : submitted / records.length,
                      strokeWidth: 13,
                      backgroundColor: const Color(0xFFE7EBF1),
                      color: const Color(0xFF007C72), // brand teal (primary)
                    ),
                    Text(
                      '${records.length}\nTotal',
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  children: [
                    _Legend(
                      label: 'In progress',
                      value: records.length - submitted,
                    ),
                    _Legend(label: 'Submitted', value: submitted),
                    const _Legend(label: 'Decision made', value: 0),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: TextButton(
              onPressed: onOpen,
              child: const Text('Go to Application Tracker'),
            ),
          ),
        ],
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.label, required this.value});
  final String label;
  final int value;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 5),
    child: Row(
      children: [
        Expanded(child: Text(label)),
        Text('$value'),
      ],
    ),
  );
}

class _SavedList extends StatelessWidget {
  const _SavedList({required this.records, required this.onViewAll});
  final List<ApplicationRecord> records;
  final VoidCallback onViewAll;

  @override
  Widget build(BuildContext context) => _Panel(
    title: 'Recently Saved Opportunities',
    onViewAll: onViewAll,
    child: records.isEmpty
        ? const Padding(
            padding: EdgeInsets.symmetric(vertical: 20),
            child: Text('No saved opportunities yet.'),
          )
        : Column(
            children: records
                .take(3)
                .map(
                  (item) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.bookmark_outline),
                    title: Text(item.opportunityTitle),
                    subtitle: Text(item.provider),
                    trailing: Text(_date(item.deadline)),
                  ),
                )
                .toList(),
          ),
  );
}

class _Notifications extends StatelessWidget {
  const _Notifications({required this.notifications, required this.onOpen});
  final List<ScholarSphereNotification> notifications;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) => _Panel(
    title: 'Latest Notifications',
    onViewAll: onOpen,
    child: notifications.isEmpty
        ? const Padding(
            padding: EdgeInsets.symmetric(vertical: 20),
            child: Text('You are all caught up.'),
          )
        : Column(
            children: notifications
                .take(3)
                .map(
                  (item) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: CircleAvatar(
                      backgroundColor: const Color(
                        0xFFE6F4F2,
                      ) /* brand teal tint */,
                      child: Icon(
                        item.type == NotificationEventType.deadlineReminder
                            ? Icons.calendar_today_outlined
                            : Icons.notifications_none,
                        size: 19,
                      ),
                    ),
                    title: Text(item.title),
                    subtitle: Text(
                      item.message,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                )
                .toList(),
          ),
  );
}

class _Panel extends StatelessWidget {
  const _Panel({
    required this.title,
    required this.child,
    required this.onViewAll,
  });
  final String title;
  final Widget child;
  final VoidCallback onViewAll;

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
              TextButton(onPressed: onViewAll, child: const Text('View all')),
            ],
          ),
          const SizedBox(height: 8),
          child,
        ],
      ),
    ),
  );
}

String _date(DateTime date) =>
    '${date.day.toString().padLeft(2, '0')} '
    '${const ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][date.month - 1]} '
    '${date.year}';
