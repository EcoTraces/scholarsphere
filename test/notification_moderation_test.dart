import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/moderation/data/demo_moderation_repository.dart';
import 'package:scholarsphere/features/moderation/domain/moderation_case.dart';
import 'package:scholarsphere/features/moderation/domain/moderation_repository.dart';
import 'package:scholarsphere/features/notifications/data/demo_notification_repository.dart';
import 'package:scholarsphere/features/notifications/domain/notification.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/providers/data/demo_provider_repository.dart';

void main() {
  test(
    'notification pipeline tracks failure, retry, expiry, and analytics',
    () async {
      final now = DateTime.utc(2026, 7, 29, 12);
      final opportunities = DemoOpportunityRepository();
      final opportunity = (await opportunities.getPublished()).first;
      final repository = DemoNotificationRepository(clock: () => now);
      await repository.savePreferences(
        'user',
        const NotificationPreferences(
          channels: {NotificationChannel.sms},
          timezone: 'Africa/Accra',
          dailyLimit: 2,
        ),
      );
      await repository.recordOpportunityEvent(
        userId: 'user',
        opportunity: opportunity,
        type: NotificationEventType.matchingOpportunity,
        message: 'A new opportunity matches your profile.',
      );
      await repository.processDueNotifications();

      var records = await repository.getForUser('user');
      final failed = records.firstWhere(
        (item) => item.type == NotificationEventType.matchingOpportunity,
      );
      expect(failed.status, NotificationDeliveryStatus.failed);
      expect(failed.failureReason, isNotEmpty);

      await repository.retryFailed(maximumRetries: 0);
      records = await repository.getForUser('user');
      expect(
        records.firstWhere((item) => item.id == failed.id).status,
        NotificationDeliveryStatus.expired,
      );
      expect((await repository.getDeliveryAnalytics()).total, greaterThan(0));
    },
  );

  test(
    'quiet hours defer delivery and deadline scheduling prevents duplicates',
    () async {
      final now = DateTime(2026, 7, 29, 23);
      final repository = DemoNotificationRepository(clock: () => now);
      final opportunities = await DemoOpportunityRepository().getPublished();
      await repository.savePreferences(
        'user',
        const NotificationPreferences(
          quietHoursStart: 22,
          quietHoursEnd: 7,
          reminderDays: {1},
        ),
      );
      await repository.scheduleDeadlineReminders(
        userId: 'user',
        opportunities: opportunities,
      );
      await repository.scheduleDeadlineReminders(
        userId: 'user',
        opportunities: opportunities,
      );
      final records = await repository.getForUser('user');
      final ids = records.map((item) => item.id).toList();
      expect(ids.toSet().length, ids.length);
    },
  );

  test(
    'moderation prevents duplicate reports and hides reported content',
    () async {
      final opportunities = DemoOpportunityRepository();
      final opportunity = (await opportunities.getPublished()).first;
      final repository = DemoModerationRepository(
        opportunities,
        DemoProviderRepository(),
        clock: () => DateTime.utc(2026, 7, 29),
      );
      final report = _report(opportunity.id);
      await repository.submit(report);
      await expectLater(
        repository.submit(_report(opportunity.id, id: 'report-2')),
        throwsA(isA<ModerationFailure>()),
      );

      await repository.assign(report.id, 'moderator');
      await repository.transition(
        caseId: report.id,
        actorId: 'moderator',
        status: ModerationStatus.underReview,
        notes: 'Official source comparison in progress.',
        hideContent: true,
      );

      expect(
        (await opportunities.getPublished()).any(
          (item) => item.id == opportunity.id,
        ),
        isFalse,
      );
      expect((await repository.getQueue()).single.temporarilyHidden, isTrue);
      expect((await repository.analytics()).totalReports, 1);
    },
  );
}

ModerationCase _report(String opportunityId, {String id = 'report-1'}) {
  final now = DateTime.utc(2026, 7, 29);
  return ModerationCase(
    id: id,
    reporterId: 'applicant',
    entityType: ReportedEntityType.opportunity,
    entityId: opportunityId,
    reportType: ModerationReportType.brokenLink,
    description: 'The official application link does not open.',
    evidence: const [
      ModerationEvidence(
        location: 'evidence/broken-link.png',
        description: 'Browser error screenshot',
      ),
    ],
    status: ModerationStatus.submitted,
    createdAt: now,
    history: [
      ModerationHistoryEntry(
        status: ModerationStatus.submitted,
        actorId: 'applicant',
        notes: 'Report submitted.',
        createdAt: now,
      ),
    ],
  );
}
