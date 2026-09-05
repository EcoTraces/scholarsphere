import 'package:flutter/material.dart';

import '../../analytics/domain/analytics_repository.dart';
import '../../calendar/domain/calendar_repository.dart';
import '../../calendar/presentation/calendar_screen.dart';
import '../../applications/domain/application_record.dart';
import '../../applications/domain/application_repository.dart';
import '../../applications/presentation/application_tracker_screen.dart';
import '../../authentication/domain/user_account.dart';
import '../../documents/domain/document_repository.dart';
import '../../fraud/domain/fraud_detection_service.dart';
import '../../guidance/domain/application_guidance_repository.dart';
import '../../experience/domain/experience_preferences.dart';
import '../../experience/domain/experience_repository.dart';
import '../../experience/presentation/experience_settings_screen.dart';
import '../../notifications/domain/notification_repository.dart';
import '../../notifications/presentation/notification_center_screen.dart';
import '../../moderation/domain/moderation_repository.dart';
import '../../profiles/domain/applicant_profile.dart';
import '../../profiles/domain/applicant_profile_repository.dart';
import '../../profiles/presentation/applicant_profile_screen.dart';
import '../../privacy/domain/privacy_models.dart';
import '../../privacy/domain/privacy_repository.dart';
import '../../privacy/domain/privacy_rules.dart';
import '../../recommendations/domain/recommendation.dart';
import '../../recommendations/domain/recommendation_engine.dart';
import '../../recommendations/domain/recommendation_governance_repository.dart';
import '../../recommendations/domain/recommendation_governance.dart';
import '../../recommendations/presentation/recommendation_controls_screen.dart';
import '../../search/domain/opportunity_filter.dart';
import '../../search/domain/opportunity_search.dart';
import '../../search/presentation/opportunity_filter_screen.dart';
import '../../search_index/domain/search_index_repository.dart';
import '../../security/domain/security_repository.dart';
import '../../security/presentation/security_privacy_center_screen.dart';
import '../../support/domain/support_repository.dart';
import '../../support/presentation/help_centre_screen.dart';
import '../domain/opportunity.dart';
import '../domain/opportunity_repository.dart';
import 'opportunity_detail_screen.dart';

class DiscoverScreen extends StatefulWidget {
  const DiscoverScreen({
    super.key,
    required this.repository,
    required this.profileRepository,
    required this.notificationRepository,
    required this.applicationRepository,
    required this.documentRepository,
    required this.analyticsRepository,
    required this.securityRepository,
    required this.privacyRepository,
    required this.recommendationGovernanceRepository,
    required this.moderationRepository,
    required this.experienceRepository,
    required this.onExperienceChanged,
    required this.searchIndexRepository,
    required this.supportRepository,
    required this.calendarRepository,
    required this.guidanceRepository,
    required this.user,
    required this.onSignOut,
  });

  final OpportunityRepository repository;
  final ApplicantProfileRepository profileRepository;
  final NotificationRepository notificationRepository;
  final ApplicationRepository applicationRepository;
  final DocumentRepository documentRepository;
  final AnalyticsRepository analyticsRepository;
  final SecurityRepository securityRepository;
  final PrivacyRepository privacyRepository;
  final RecommendationGovernanceRepository recommendationGovernanceRepository;
  final ModerationRepository moderationRepository;
  final ExperienceRepository experienceRepository;
  final ValueChanged<ExperiencePreferences> onExperienceChanged;
  final SearchIndexRepository searchIndexRepository;
  final SupportRepository supportRepository;
  final CalendarRepository calendarRepository;
  final ApplicationGuidanceRepository guidanceRepository;
  final UserAccount user;
  final VoidCallback onSignOut;

  @override
  State<DiscoverScreen> createState() => _DiscoverScreenState();
}

class _DiscoverScreenState extends State<DiscoverScreen> {
  late Future<
    ({
      List<Opportunity> opportunities,
      ApplicantProfile profile,
      List<ApplicationRecord> applications,
      bool personalizationEnabled,
      PersonalizationControls recommendationControls,
    })
  >
  _data;
  final _search = const OpportunitySearch();
  final _recommendations = const RecommendationEngine();
  final _fraudDetection = FraudDetectionService();
  final List<String> _previousSearches = [];
  OpportunityFilter _filter = const OpportunityFilter();
  RecommendationCategory? _category;

  @override
  void initState() {
    super.initState();
    _data = _loadData();
  }

  Future<
    ({
      List<Opportunity> opportunities,
      ApplicantProfile profile,
      List<ApplicationRecord> applications,
      bool personalizationEnabled,
      PersonalizationControls recommendationControls,
    })
  >
  _loadData() async {
    final opportunities = await widget.repository.getPublished();
    await widget.searchIndexRepository.synchronize(opportunities);
    final profile =
        await widget.profileRepository.getForUser(widget.user.id) ??
        ApplicantProfile.empty(widget.user);
    await widget.privacyRepository.setMinorStatus(
      widget.user.id,
      PrivacyRules.isMinor(profile.dateOfBirth, DateTime.now()),
    );
    final applications = await widget.applicationRepository.getForUser(
      widget.user.id,
    );
    final consents = await widget.privacyRepository.getConsents(widget.user.id);
    final personalizationEnabled = consents.any(
      (consent) =>
          consent.type == ConsentType.personalizedRecommendations &&
          consent.isActive,
    );
    final recommendationControls = await widget
        .recommendationGovernanceRepository
        .getControls(widget.user.id);
    final governedProfile = recommendationControls.preferredCountries.isEmpty
        ? profile
        : profile.copyWith(
            preferredCountries: recommendationControls.preferredCountries,
          );
    return (
      opportunities: opportunities,
      profile: governedProfile,
      applications: applications,
      personalizationEnabled: personalizationEnabled,
      recommendationControls: recommendationControls,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.public),
            SizedBox(width: 10),
            Text(
              'ScholarSphere',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: _openNotifications,
            tooltip: 'Notifications',
            icon: const Icon(Icons.notifications_none),
          ),
          PopupMenuButton<String>(
            tooltip: 'Account',
            icon: const Icon(Icons.account_circle_outlined),
            onSelected: (value) {
              if (value == 'profile') {
                _openProfile();
              }
              if (value == 'security-privacy') {
                _openSecurityPrivacy();
              }
              if (value == 'recommendations') {
                _openRecommendationControls();
              }
              if (value == 'experience') {
                _openExperienceSettings();
              }
              if (value == 'help') {
                _openHelpCentre();
              }
              if (value == 'calendar') {
                _openCalendar();
              }
              if (value == 'sign-out') widget.onSignOut();
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                enabled: false,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.user.fullName,
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    Text(widget.user.roleLabel),
                  ],
                ),
              ),
              const PopupMenuDivider(),
              const PopupMenuItem(
                value: 'calendar',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.calendar_month_outlined),
                  title: Text('Application calendar'),
                ),
              ),
              const PopupMenuItem(
                value: 'help',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.help_outline),
                  title: Text('Help centre'),
                ),
              ),
              const PopupMenuItem(
                value: 'experience',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.accessibility_new),
                  title: Text('Language and accessibility'),
                ),
              ),
              const PopupMenuItem(
                value: 'recommendations',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.tune),
                  title: Text('Recommendation controls'),
                ),
              ),
              const PopupMenuItem(
                value: 'profile',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.manage_accounts_outlined),
                  title: Text('Edit profile'),
                ),
              ),
              const PopupMenuItem(
                value: 'security-privacy',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.security_outlined),
                  title: Text('Security and privacy'),
                ),
              ),
              const PopupMenuItem(
                value: 'sign-out',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.logout),
                  title: Text('Sign out'),
                ),
              ),
            ],
          ),
          const SizedBox(width: 8),
        ],
      ),
      body:
          FutureBuilder<
            ({
              List<Opportunity> opportunities,
              ApplicantProfile profile,
              List<ApplicationRecord> applications,
              bool personalizationEnabled,
              PersonalizationControls recommendationControls,
            })
          >(
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
                        const Text('Opportunities could not be loaded.'),
                        const SizedBox(height: 16),
                        FilledButton.icon(
                          onPressed: () => setState(() => _data = _loadData()),
                          icon: const Icon(Icons.refresh),
                          label: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                );
              }
              if (!snapshot.hasData) {
                return const Center(child: CircularProgressIndicator());
              }

              final data = snapshot.data!;
              var results = _search.apply(data.opportunities, _filter);
              results = results
                  .where(
                    (item) => !data.recommendationControls.hiddenOpportunityIds
                        .contains(item.id),
                  )
                  .toList();
              final category = _category;
              final categoryAllowed =
                  data.recommendationControls.opportunityCategories.isEmpty ||
                  (category != null &&
                      data.recommendationControls.opportunityCategories
                          .contains(category));
              if (category != null &&
                  data.personalizationEnabled &&
                  categoryAllowed) {
                results = _recommendations
                    .recommend(
                      opportunities: results,
                      profile: data.profile,
                      category: category,
                      signals: RecommendationSignals(
                        previousSearches:
                            data
                                .recommendationControls
                                .behaviouralRecommendationsEnabled
                            ? _previousSearches
                            : const [],
                        savedOpportunityIds: data.applications
                            .where(
                              (item) =>
                                  item.stage == ApplicationStage.saved ||
                                  item.stage == ApplicationStage.interested,
                            )
                            .map((item) => item.opportunityId)
                            .toSet(),
                        appliedOpportunityIds: data.applications
                            .where(
                              (item) =>
                                  item.stage != ApplicationStage.saved &&
                                  item.stage != ApplicationStage.interested,
                            )
                            .map((item) => item.opportunityId)
                            .toSet(),
                      ),
                    )
                    .map((item) => item.opportunity)
                    .toList();
              }
              return ListView(
                padding: const EdgeInsets.fromLTRB(20, 24, 20, 40),
                children: [
                  Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 1080),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Find your next opportunity',
                            style: Theme.of(context).textTheme.headlineLarge,
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Search trusted scholarships, fellowships, internships, and events.',
                          ),
                          const SizedBox(height: 22),
                          TextField(
                            key: const Key('opportunity-search'),
                            onChanged: (value) => setState(
                              () => _filter = _filter.copyWith(query: value),
                            ),
                            onSubmitted: (value) {
                              final query = value.trim();
                              if (query.isNotEmpty &&
                                  !_previousSearches.contains(query)) {
                                setState(() => _previousSearches.add(query));
                              }
                            },
                            decoration: const InputDecoration(
                              prefixIcon: Icon(Icons.search),
                              hintText: 'Search by title, provider, or country',
                            ),
                          ),
                          const SizedBox(height: 14),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              OutlinedButton.icon(
                                onPressed: _openFilters,
                                icon: const Icon(Icons.filter_alt_outlined),
                                label: Text(
                                  _filter.activeCount == 0
                                      ? 'Filters'
                                      : 'Filters (${_filter.activeCount})',
                                ),
                              ),
                              ChoiceChip(
                                label: const Text('All opportunities'),
                                selected: _category == null,
                                onSelected: (_) =>
                                    setState(() => _category = null),
                              ),
                              ...RecommendationCategory.values.map(
                                (category) => ChoiceChip(
                                  label: Text(_categoryLabel(category)),
                                  selected: _category == category,
                                  onSelected: data.personalizationEnabled
                                      ? (_) =>
                                            setState(() => _category = category)
                                      : null,
                                ),
                              ),
                              if (!data.personalizationEnabled)
                                const Chip(
                                  avatar: Icon(Icons.privacy_tip_outlined),
                                  label: Text(
                                    'Personalized recommendations disabled',
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: 28),
                          Text(
                            '${results.length} opportunities',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 12),
                          if (results.isEmpty)
                            const _EmptyResults()
                          else
                            LayoutBuilder(
                              builder: (context, constraints) {
                                final columns = constraints.maxWidth >= 850
                                    ? 2
                                    : 1;
                                return GridView.builder(
                                  shrinkWrap: true,
                                  physics: const NeverScrollableScrollPhysics(),
                                  itemCount: results.length,
                                  gridDelegate:
                                      SliverGridDelegateWithFixedCrossAxisCount(
                                        crossAxisCount: columns,
                                        crossAxisSpacing: 14,
                                        mainAxisSpacing: 14,
                                        mainAxisExtent: 270,
                                      ),
                                  itemBuilder: (_, index) => _OpportunityCard(
                                    opportunity: results[index],
                                    onTap: () =>
                                        _openOpportunity(results[index]),
                                  ),
                                );
                              },
                            ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 0,
        onDestinationSelected: (index) {
          if (index == 1) _openApplications(savedOnly: true);
          if (index == 2) _openApplications();
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.explore_outlined),
            label: 'Discover',
          ),
          NavigationDestination(
            icon: Icon(Icons.bookmark_outline),
            label: 'Saved',
          ),
          NavigationDestination(
            icon: Icon(Icons.fact_check_outlined),
            label: 'Applications',
          ),
        ],
      ),
    );
  }

  Future<void> _openFilters() async {
    final filter = await Navigator.of(context).push<OpportunityFilter>(
      MaterialPageRoute(
        builder: (context) => OpportunityFilterScreen(initial: _filter),
      ),
    );
    if (filter != null && mounted) setState(() => _filter = filter);
  }

  Future<void> _openProfile() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (context) => ApplicantProfileScreen(
          user: widget.user,
          repository: widget.profileRepository,
        ),
      ),
    );
    if (mounted) setState(() => _data = _loadData());
  }

  Future<void> _openSecurityPrivacy() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (context) => SecurityPrivacyCenterScreen(
          user: widget.user,
          securityRepository: widget.securityRepository,
          privacyRepository: widget.privacyRepository,
          profileRepository: widget.profileRepository,
          applicationRepository: widget.applicationRepository,
          documentRepository: widget.documentRepository,
        ),
      ),
    );
    if (mounted) setState(() => _data = _loadData());
  }

  Future<void> _openRecommendationControls() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (context) => RecommendationControlsScreen(
          userId: widget.user.id,
          repository: widget.recommendationGovernanceRepository,
        ),
      ),
    );
    if (mounted) setState(() => _data = _loadData());
  }

  Future<void> _openExperienceSettings() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (context) => ExperienceSettingsScreen(
          userId: widget.user.id,
          repository: widget.experienceRepository,
          onChanged: widget.onExperienceChanged,
        ),
      ),
    );
  }

  Future<void> _openHelpCentre() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => HelpCentreScreen(
          userId: widget.user.id,
          repository: widget.supportRepository,
        ),
      ),
    );
  }

  Future<void> _openCalendar() async {
    final data = await _data;
    if (!mounted) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => CalendarScreen(
          userId: widget.user.id,
          opportunities: data.opportunities,
          applications: data.applications,
          repository: widget.calendarRepository,
        ),
      ),
    );
  }

  Future<void> _openNotifications() async {
    final data = await _data;
    if (!mounted) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (context) => NotificationCenterScreen(
          userId: widget.user.id,
          opportunities: data.opportunities,
          repository: widget.notificationRepository,
        ),
      ),
    );
  }

  Future<void> _openOpportunity(Opportunity opportunity) async {
    final data = await _data;
    await widget.analyticsRepository.recordOpportunityView(
      userId: widget.user.id,
      opportunityId: opportunity.id,
    );
    final assessment = _fraudDetection.assess(
      opportunity,
      knownOpportunities: data.opportunities,
    );
    if (!mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => OpportunityDetailScreen(
          opportunity: opportunity,
          profile: data.profile,
          fraudAssessment: assessment,
          userId: widget.user.id,
          applicationRepository: widget.applicationRepository,
          documentRepository: widget.documentRepository,
          moderationRepository: widget.moderationRepository,
          guidanceRepository: widget.guidanceRepository,
        ),
      ),
    );
    if (mounted) setState(() => _data = _loadData());
  }

  Future<void> _openApplications({bool savedOnly = false}) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (context) => ApplicationTrackerScreen(
          userId: widget.user.id,
          repository: widget.applicationRepository,
          savedOnly: savedOnly,
        ),
      ),
    );
    if (mounted) setState(() => _data = _loadData());
  }

  String _categoryLabel(RecommendationCategory category) => switch (category) {
    RecommendationCategory.bestMatches => 'Best matches',
    RecommendationCategory.newlyPublished => 'Newly published',
    RecommendationCategory.fullyFunded => 'Fully funded',
    RecommendationCategory.noApplicationFee => 'No application fee',
    RecommendationCategory.closingSoon => 'Closing soon',
    RecommendationCategory.suitableForCountry => 'For your country',
    RecommendationCategory.suitableForDegree => 'For your degree',
    RecommendationCategory.online => 'Online',
    RecommendationCategory.noIelts => 'No IELTS',
    RecommendationCategory.undergraduate => 'Undergraduate',
    RecommendationCategory.masters => 'Master\'s',
    RecommendationCategory.phd => 'PhD',
    RecommendationCategory.professional => 'Professional',
  };
}

class _OpportunityCard extends StatelessWidget {
  const _OpportunityCard({required this.opportunity, required this.onTap});

  final Opportunity opportunity;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final deadline = _formatDeadline(opportunity.deadline);
    final closingSoon =
        opportunity.deadline.difference(DateTime.now()).inDays <= 14;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    opportunity.typeLabel,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.primary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const Spacer(),
                  if (opportunity.isVerified)
                    const Tooltip(
                      message: 'Verified from an official source',
                      child: Icon(Icons.verified, color: Color(0xFF007C72)),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                opportunity.title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 6),
              Text('${opportunity.provider} | ${opportunity.hostCountry}'),
              const Spacer(),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  Chip(label: Text(opportunity.fundingLabel)),
                  Chip(label: Text(opportunity.studyLevels.first)),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Icon(
                    closingSoon ? Icons.schedule : Icons.event_outlined,
                    size: 18,
                    color: closingSoon
                        ? Theme.of(context).colorScheme.error
                        : null,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    closingSoon
                        ? 'Closing soon · $deadline'
                        : 'Deadline $deadline',
                    style: closingSoon
                        ? TextStyle(
                            color: Theme.of(context).colorScheme.error,
                            fontWeight: FontWeight.w700,
                          )
                        : null,
                  ),
                  const Spacer(),
                  const Icon(Icons.arrow_forward, size: 20),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

const _months = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

// A day/month/year slash format (e.g. "3/7/2027") is ambiguous across
// locales — this reads unambiguously regardless of the viewer's country.
String _formatDeadline(DateTime date) =>
    '${date.day.toString().padLeft(2, '0')} '
    '${_months[date.month - 1]} '
    '${date.year}';

class _EmptyResults extends StatelessWidget {
  const _EmptyResults();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 56),
      child: Center(
        child: Column(
          children: [
            Icon(Icons.search_off, size: 42),
            SizedBox(height: 12),
            Text('No opportunities match these filters.'),
          ],
        ),
      ),
    );
  }
}
