import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/notifications/data/demo_notification_repository.dart';
import 'package:scholarsphere/features/notifications/domain/notification.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';

void main() {
  test('deadline scheduler creates every configured reminder', () async {
    final repository = DemoNotificationRepository(
      clock: () => DateTime(2026, 7, 28),
    );
    final opportunities = await DemoOpportunityRepository().getPublished();

    await repository.scheduleDeadlineReminders(
      userId: 'applicant',
      opportunities: opportunities,
    );
    final records = await repository.getForUser('applicant');
    final reminders = records
        .where((item) => item.type == NotificationEventType.deadlineReminder)
        .toList();

    expect(reminders.length, opportunities.length * 5);
    expect(
      reminders.any((item) => item.title == '1-day deadline reminder'),
      isTrue,
    );
  });

  test('disabled preferences suppress opportunity events', () async {
    final repository = DemoNotificationRepository(
      clock: () => DateTime(2026, 7, 28),
    );
    final opportunity =
        (await DemoOpportunityRepository().getPublished()).first;
    await repository.savePreferences(
      'applicant',
      const NotificationPreferences(frequency: NotificationFrequency.disabled),
    );

    await repository.recordOpportunityEvent(
      userId: 'applicant',
      opportunity: opportunity,
      type: NotificationEventType.opportunityVerified,
      message: 'This opportunity was verified.',
    );
    final records = await repository.getForUser('applicant');

    expect(
      records.where(
        (item) => item.type == NotificationEventType.opportunityVerified,
      ),
      isEmpty,
    );
  });
}
