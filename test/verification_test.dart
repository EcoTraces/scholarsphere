import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/opportunities/domain/opportunity.dart';
import 'package:scholarsphere/features/verification/data/demo_verification_repository.dart';
import 'package:scholarsphere/features/verification/domain/verification_review.dart';

void main() {
  const completeChecklist = VerificationChecklist(
    officialWebsiteChecked: true,
    sponsorConfirmed: true,
    applicationLinkTested: true,
    deadlineConfirmed: true,
    requirementsReviewed: true,
    duplicatesChecked: true,
  );
  const detailedChecklist = VerificationChecklist(
    officialWebsiteChecked: true,
    sponsorConfirmed: true,
    applicationLinkTested: true,
    deadlineConfirmed: true,
    requirementsReviewed: true,
    duplicatesChecked: true,
    organizationExists: true,
    applicationOpen: true,
    fundingConfirmed: true,
    feesConfirmed: true,
    contactDetailsConfirmed: true,
    noMisleadingClaims: true,
    supportingEvidenceStored: true,
  );

  test('third-party sources cannot verify an opportunity', () async {
    final opportunities = DemoOpportunityRepository();
    final repository = DemoVerificationRepository(opportunities);
    final queue = await repository.getQueue();

    await expectLater(
      repository.submitReview(
        VerificationReview(
          opportunityId: queue.first.id,
          sourceAuthority: SourceAuthority.unverifiedThirdParty,
          checklist: completeChecklist,
          status: VerificationStatus.verified,
          notes: 'Found on several blogs.',
          reviewedByUserId: 'officer',
          reviewedAt: DateTime(2026, 7, 21),
          nextReviewAt: DateTime(2026, 10, 19),
        ),
      ),
      throwsA(isA<VerificationFailure>()),
    );
  });

  test('complete official review publishes the opportunity', () async {
    final opportunities = DemoOpportunityRepository();
    final repository = DemoVerificationRepository(opportunities);
    final queue = await repository.getQueue();
    final candidate = queue.first;

    await repository.submitReview(
      VerificationReview(
        opportunityId: candidate.id,
        sourceAuthority: SourceAuthority.officialInstitution,
        checklist: completeChecklist,
        status: VerificationStatus.verified,
        notes: 'Checked against the official institution website.',
        reviewedByUserId: 'officer',
        reviewedAt: DateTime(2026, 7, 21),
        nextReviewAt: DateTime(2026, 10, 19),
      ),
    );

    final published = await opportunities.getPublished();
    expect(published.any((item) => item.id == candidate.id), isTrue);
  });

  test(
    'detailed workflow requires a different second-level approver',
    () async {
      final opportunities = DemoOpportunityRepository();
      final repository = DemoVerificationRepository(
        opportunities,
        clock: () => DateTime.utc(2026, 7, 29),
      );
      final candidate = (await repository.getQueue()).first;
      await repository.assign(
        opportunityId: candidate.id,
        officerId: 'officer-1',
        assignedByUserId: 'administrator',
      );
      final submitted = await repository.submitForSecondApproval(
        VerificationReview(
          verificationId: 'verification-1',
          opportunityId: candidate.id,
          assignedToUserId: 'officer-1',
          sourceAuthority: SourceAuthority.officialInstitution,
          checklist: detailedChecklist,
          status: VerificationStatus.pending,
          workflowStatus: VerificationWorkflowStatus.underReview,
          officialSourceUrl: candidate.officialSourceUrl,
          evidenceLocation: 'evidence/verification-1',
          notes: 'All official records checked.',
          reviewedByUserId: 'officer-1',
          reviewedAt: DateTime.utc(2026, 7, 29),
          nextReviewAt: DateTime.utc(2026, 10, 27),
        ),
      );

      await expectLater(
        repository.approveSecondLevel(
          verificationId: submitted.verificationId!,
          approverId: 'officer-1',
        ),
        throwsA(isA<VerificationFailure>()),
      );
      final approved = await repository.approveSecondLevel(
        verificationId: submitted.verificationId!,
        approverId: 'officer-2',
      );

      expect(approved.workflowStatus, VerificationWorkflowStatus.verified);
      expect(approved.approvedByUserId, 'officer-2');
      expect((await repository.getHistory(candidate.id)), hasLength(3));
      expect(
        (await opportunities.getPublished()).any(
          (item) => item.id == candidate.id,
        ),
        isTrue,
      );
    },
  );
}
