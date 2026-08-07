import '../../opportunities/domain/opportunity.dart';
import 'verification_review.dart';

abstract interface class VerificationRepository {
  Future<List<Opportunity>> getQueue();

  Future<VerificationReview?> getLatestReview(String opportunityId);

  Future<void> submitReview(VerificationReview review);
  Future<VerificationReview> assign({
    required String opportunityId,
    required String officerId,
    required String assignedByUserId,
  });
  Future<VerificationReview> submitForSecondApproval(VerificationReview review);
  Future<VerificationReview> approveSecondLevel({
    required String verificationId,
    required String approverId,
  });
  Future<List<VerificationReview>> getHistory(String opportunityId);
  Future<VerificationReview> requestCorrection({
    required String opportunityId,
    required String requestedBy,
    required String notes,
  });
  Future<VerificationReview> appeal({
    required String opportunityId,
    required String requestedBy,
    required String reason,
  });
  Future<VerificationReview> resolveConflict({
    required String opportunityId,
    required String resolverId,
    required VerificationWorkflowStatus resolution,
    required String notes,
  });

  Future<List<VerificationReview>> getAllForAdministration();
}
