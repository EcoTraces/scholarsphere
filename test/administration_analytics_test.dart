import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/administration/domain/administration_analytics_service.dart';
import 'package:scholarsphere/features/analytics/data/demo_analytics_repository.dart';
import 'package:scholarsphere/features/applications/data/demo_application_repository.dart';
import 'package:scholarsphere/features/applications/domain/application_record.dart';
import 'package:scholarsphere/features/authentication/data/demo_auth_repository.dart';
import 'package:scholarsphere/features/notifications/data/demo_notification_repository.dart';
import 'package:scholarsphere/features/notifications/domain/notification.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/profiles/data/demo_applicant_profile_repository.dart';
import 'package:scholarsphere/features/profiles/domain/applicant_profile.dart';
import 'package:scholarsphere/features/verification/data/demo_verification_repository.dart';

void main() {
  test('administration snapshots aggregate repository activity', () async {
    final now = DateTime(2026, 7, 29);
    final auth = DemoAuthRepository();
    final opportunities = DemoOpportunityRepository();
    final applications = DemoApplicationRepository(clock: () => now);
    final profiles = DemoApplicantProfileRepository();
    final notifications = DemoNotificationRepository(clock: () => now);
    final verification = DemoVerificationRepository(opportunities);
    final analytics = DemoAnalyticsRepository();
    final published = await opportunities.getPublished();

    final saved = await applications.saveOpportunity(
      'demo-applicant',
      published.first,
    );
    await applications.update(saved.copyWith(stage: ApplicationStage.accepted));
    await profiles.save(
      ApplicantProfile(
        userId: 'demo-applicant',
        fullName: 'Demo Applicant',
        nationality: 'Ghana',
        countryOfResidence: 'Ghana',
        dateOfBirth: null,
        gender: '',
        highestQualification: 'Bachelor',
        degreeField: 'Computer science',
        academicClassification: '',
        graduationYear: 2025,
        workExperienceYears: 1,
        preferredStudyLevels: const ['Master\'s'],
        preferredCountries: const ['Germany'],
        areasOfInterest: const ['Climate'],
        englishTestStatus: EnglishTestStatus.completed,
        passportStatus: PassportStatus.valid,
        employmentStatus: EmploymentStatus.student,
        fundingPreferences: const ['Fully funded'],
        specialEligibilityCategories: const [],
        documents: const [],
      ),
    );
    await analytics.recordOpportunityView(
      userId: 'demo-applicant',
      opportunityId: published.first.id,
    );
    await analytics.recordOpportunityView(
      userId: 'demo-applicant',
      opportunityId: published.first.id,
    );
    await notifications.recordOpportunityEvent(
      userId: 'demo-applicant',
      opportunity: published.first,
      type: NotificationEventType.opportunityVerified,
      message: 'Verified.',
    );
    final userNotifications = await notifications.getForUser('demo-applicant');
    await notifications.markRead('demo-applicant', userNotifications.first.id);

    final service = AdministrationAnalyticsService(
      authRepository: auth,
      opportunityRepository: opportunities,
      applicationRepository: applications,
      profileRepository: profiles,
      notificationRepository: notifications,
      verificationRepository: verification,
      analyticsRepository: analytics,
      clock: () => now,
    );
    final data = await service.load();

    expect(data.dashboard.totalOpportunities, 4);
    expect(data.dashboard.verifiedOpportunities, 3);
    expect(data.dashboard.pendingVerification, 1);
    expect(data.dashboard.registeredApplicants, 1);
    expect(data.dashboard.registeredProviders, 1);
    expect(data.dashboard.trackedApplications, 1);
    expect(data.dashboard.mostViewed.first.value, 2);
    expect(data.reports.applicationConversionRate, 1);
    expect(data.reports.notificationEngagement, 1);
    expect(
      data.reports.userInterestByField.map((item) => item.label),
      contains('Computer science'),
    );
    expect(
      data.reports.successfulProviders.first.label,
      published.first.provider,
    );
  });
}
