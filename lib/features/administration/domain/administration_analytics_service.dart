import '../../analytics/domain/analytics_repository.dart';
import '../../applications/domain/application_record.dart';
import '../../applications/domain/application_repository.dart';
import '../../authentication/domain/auth_repository.dart';
import '../../authentication/domain/user_account.dart';
import '../../notifications/domain/notification_repository.dart';
import '../../opportunities/domain/opportunity.dart';
import '../../opportunities/domain/opportunity_repository.dart';
import '../../profiles/domain/applicant_profile_repository.dart';
import '../../search/domain/opportunity_search.dart';
import '../../verification/domain/verification_repository.dart';
import 'administration_snapshot.dart';

class AdministrationAnalyticsService {
  AdministrationAnalyticsService({
    required this.authRepository,
    required this.opportunityRepository,
    required this.applicationRepository,
    required this.profileRepository,
    required this.notificationRepository,
    required this.verificationRepository,
    required this.analyticsRepository,
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now;

  final AuthRepository authRepository;
  final OpportunityRepository opportunityRepository;
  final ApplicationRepository applicationRepository;
  final ApplicantProfileRepository profileRepository;
  final NotificationRepository notificationRepository;
  final VerificationRepository verificationRepository;
  final AnalyticsRepository analyticsRepository;
  final DateTime Function() _clock;

  Future<AdministrationData> load() async {
    final users = await authRepository.getAllForAdministration();
    final opportunities = await opportunityRepository.getAllForAdministration();
    final applications = await applicationRepository.getAllForAdministration();
    final profiles = await profileRepository.getAllForAdministration();
    final notifications = await notificationRepository
        .getAllForAdministration();
    final reviews = await verificationRepository.getAllForAdministration();
    final views = await analyticsRepository.getOpportunityViewCounts();
    final now = _clock();

    final expired = opportunities
        .where(
          (item) =>
              !item.deadline.isAfter(now) ||
              item.verificationStatus == VerificationStatus.expired,
        )
        .toList();
    final closing =
        opportunities
            .where(
              (item) =>
                  item.deadline.isAfter(now) &&
                  !item.deadline.isAfter(now.add(const Duration(days: 30))),
            )
            .toList()
          ..sort((left, right) => left.deadline.compareTo(right.deadline));

    final dashboard = AdministrationDashboardSnapshot(
      totalOpportunities: opportunities.length,
      activeOpportunities: opportunities.where((item) {
        return item.deadline.isAfter(now) &&
            !{
              VerificationStatus.expired,
              VerificationStatus.rejected,
              VerificationStatus.archived,
            }.contains(item.verificationStatus);
      }).length,
      verifiedOpportunities: opportunities
          .where((item) => item.isVerified)
          .length,
      pendingVerification: opportunities
          .where(
            (item) =>
                item.verificationStatus == VerificationStatus.pending ||
                item.verificationStatus ==
                    VerificationStatus.verificationExpired,
          )
          .length,
      expiredOpportunities: expired.length,
      suspiciousSubmissions: opportunities
          .where(
            (item) => item.verificationStatus == VerificationStatus.suspicious,
          )
          .length,
      registeredApplicants: users
          .where((user) => user.role == UserRole.applicant)
          .length,
      registeredProviders: users
          .where((user) => user.role == UserRole.opportunityProvider)
          .length,
      trackedApplications: applications.length,
      mostViewed: _rankViews(opportunities, views),
      popularCountries: _rankOpportunityProperty(
        opportunities,
        views,
        (item) => [item.hostCountry],
      ),
      popularFields: _rankOpportunityProperty(opportunities, views, (item) {
        return item.fieldsOfStudy;
      }),
      closingSoon: closing
          .take(5)
          .map(
            (item) => RankedMetric(
              label: item.title,
              value: item.deadline.difference(now).inDays,
            ),
          )
          .toList(),
      notificationStatistics: [
        RankedMetric(label: 'Scheduled', value: notifications.length),
        RankedMetric(
          label: 'Delivered',
          value: notifications
              .where((item) => !item.scheduledFor.isAfter(now))
              .length,
        ),
        RankedMetric(
          label: 'Read',
          value: notifications.where((item) => item.isRead).length,
        ),
      ],
    );

    final submittedStages = {
      ApplicationStage.applicationSubmitted,
      ApplicationStage.interviewStage,
      ApplicationStage.waitingForDecision,
      ApplicationStage.accepted,
      ApplicationStage.rejected,
    };
    final submitted = applications.where(
      (item) => submittedStages.contains(item.stage),
    );
    final delivered = notifications
        .where((item) => !item.scheduledFor.isAfter(now))
        .toList();
    final reports = ReportingSnapshot(
      opportunitiesByCountry: _rankCounts(
        opportunities.map((item) => item.hostCountry),
      ),
      opportunitiesByContinent: _rankCounts(
        opportunities.map(
          (item) =>
              Geography.regionFor(item.hostCountry)?.name ?? 'unclassified',
        ),
      ),
      scholarshipsByStudyLevel: _rankCounts(
        opportunities
            .where((item) => item.type == OpportunityType.scholarship)
            .expand((item) => item.studyLevels),
      ),
      opportunitiesByFunding: _rankCounts(
        opportunities.map((item) => item.fundingLabel),
      ),
      applicationConversionRate: applications.isEmpty
          ? 0
          : submitted.length / applications.length,
      userInterestByField: _rankCounts(
        profiles.expand(
          (profile) => {
            if (profile.degreeField.isNotEmpty) profile.degreeField,
            ...profile.areasOfInterest,
          },
        ),
      ),
      successfulProviders: _rankCounts(
        applications
            .where((item) => item.stage == ApplicationStage.accepted)
            .map((item) => item.provider),
      ),
      verificationActivity: _rankCounts(
        reviews.map((review) => review.status.name),
      ),
      expiredOpportunityReport: expired
          .map(
            (item) => RankedMetric(
              label: item.title,
              value: now.difference(item.deadline).inDays.clamp(0, 99999),
            ),
          )
          .toList(),
      notificationEngagement: delivered.isEmpty
          ? 0
          : delivered.where((item) => item.isRead).length / delivered.length,
      applicationOutcomes: _rankCounts(
        applications.map((item) => item.stageLabel),
      ),
    );
    return AdministrationData(dashboard: dashboard, reports: reports);
  }

  List<RankedMetric> _rankViews(
    List<Opportunity> opportunities,
    Map<String, int> views,
  ) =>
      opportunities
          .where((item) => (views[item.id] ?? 0) > 0)
          .map(
            (item) =>
                RankedMetric(label: item.title, value: views[item.id] ?? 0),
          )
          .toList()
        ..sort((left, right) => right.value.compareTo(left.value));

  List<RankedMetric> _rankOpportunityProperty(
    List<Opportunity> opportunities,
    Map<String, int> views,
    Iterable<String> Function(Opportunity) select,
  ) {
    final values = <String, int>{};
    final hasViews = views.values.any((count) => count > 0);
    for (final opportunity in opportunities) {
      final weight = hasViews ? views[opportunity.id] ?? 0 : 1;
      for (final value in select(opportunity)) {
        values.update(value, (count) => count + weight, ifAbsent: () => weight);
      }
    }
    return _rankMap(values);
  }

  List<RankedMetric> _rankCounts(Iterable<String> values) {
    final counts = <String, int>{};
    for (final value in values.where((item) => item.trim().isNotEmpty)) {
      counts.update(value, (count) => count + 1, ifAbsent: () => 1);
    }
    return _rankMap(counts);
  }

  List<RankedMetric> _rankMap(Map<String, int> values) {
    final ranked =
        values.entries
            .map((entry) => RankedMetric(label: entry.key, value: entry.value))
            .toList()
          ..sort((left, right) => right.value.compareTo(left.value));
    return ranked.take(8).toList();
  }
}
