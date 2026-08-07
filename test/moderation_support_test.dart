import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/moderation/data/demo_moderation_repository.dart';
import 'package:scholarsphere/features/moderation/domain/moderation_case.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/providers/data/demo_provider_repository.dart';
import 'package:scholarsphere/features/support/data/demo_support_repository.dart';
import 'package:scholarsphere/features/support/domain/support_models.dart';
import 'package:scholarsphere/features/support/domain/support_repository.dart';

void main() {
  test('moderators can issue and retrieve provider warnings', () async {
    final now = DateTime.utc(2026, 7, 29);
    final repository = DemoModerationRepository(
      DemoOpportunityRepository(),
      DemoProviderRepository(),
      clock: () => now,
    );
    final report = ModerationCase(
      id: 'provider-report',
      reporterId: 'applicant',
      entityType: ReportedEntityType.provider,
      entityId: 'provider-1',
      reportType: ModerationReportType.misleadingContent,
      description: 'The provider published an unsupported claim.',
      evidence: const [],
      status: ModerationStatus.submitted,
      createdAt: now,
      history: const [],
    );
    await repository.submit(report);
    await repository.issueWarning(
      caseId: report.id,
      moderatorId: 'moderator',
      reason: 'Remove the unsupported guarantee.',
    );

    final warnings = await repository.warningsFor(
      ReportedEntityType.provider,
      'provider-1',
    );
    expect(warnings, hasLength(1));
    expect(warnings.single.caseId, report.id);
    expect((await repository.getQueue()), isEmpty);
  });

  test(
    'support tickets track assignment, messages, notes, SLA, and surveys',
    () async {
      var now = DateTime.utc(2026, 7, 29, 9);
      final repository = DemoSupportRepository(clock: () => now);
      final ticket = await repository.submitTicket(
        requesterId: 'applicant',
        subject: 'Cannot update my profile',
        category: SupportTicketCategory.profileProblem,
        priority: SupportTicketPriority.high,
        message: 'The graduation year field does not save.',
      );
      expect(ticket.firstResponseDueAt, now.add(const Duration(hours: 2)));

      now = now.add(const Duration(minutes: 30));
      await repository.assign(ticket.id, 'support-agent');
      await repository.addInternalNote(
        ticket.id,
        'support-agent',
        'Reproduced on the profile form.',
      );
      await repository.addMessage(
        ticketId: ticket.id,
        senderId: 'support-agent',
        message: 'We are investigating the profile form.',
        isAgent: true,
      );
      now = now.add(const Duration(hours: 1));
      await repository.updateStatus(
        ticket.id,
        'support-agent',
        SupportTicketStatus.resolved,
        notes: 'Profile save corrected.',
      );
      await repository.submitSurvey(
        SatisfactionSurvey(
          ticketId: ticket.id,
          userId: 'applicant',
          rating: 5,
          createdAt: now,
          comment: 'Resolved quickly.',
        ),
      );

      final resolved = await repository.getById(ticket.id);
      expect(resolved?.messages, hasLength(2));
      expect(resolved?.internalNotes, hasLength(1));
      final report = await repository.performanceReport();
      expect(report.totalTickets, 1);
      expect(report.averageFirstResponseMinutes, 30);
      expect(report.satisfactionScore, 5);
    },
  );

  test(
    'knowledge, templates, and attachment restrictions are enforced',
    () async {
      final repository = DemoSupportRepository();
      expect(await repository.searchKnowledge('eligibility'), isNotEmpty);
      await repository.saveTemplate(
        const SupportResponseTemplate(
          id: 'template-1',
          name: 'Profile troubleshooting',
          category: SupportTicketCategory.profileProblem,
          subject: 'Profile troubleshooting steps',
          body: 'Please confirm each required profile field is complete.',
        ),
      );
      expect(
        await repository.templates(SupportTicketCategory.profileProblem),
        hasLength(1),
      );
      await expectLater(
        repository.submitTicket(
          requesterId: 'applicant',
          subject: 'Attachment',
          category: SupportTicketCategory.technicalIssue,
          priority: SupportTicketPriority.normal,
          message: 'Please review this attachment.',
          attachments: const [
            SupportAttachment(
              id: 'attachment-1',
              name: 'unsafe.exe',
              storageLocation: 'uploads/unsafe.exe',
              contentType: 'application/x-msdownload',
              sizeBytes: 100,
            ),
          ],
        ),
        throwsA(isA<SupportFailure>()),
      );
    },
  );
}
