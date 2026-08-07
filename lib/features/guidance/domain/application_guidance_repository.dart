import '../../documents/domain/document_readiness.dart';
import '../../opportunities/domain/opportunity.dart';
import '../../profiles/domain/applicant_profile.dart';
import 'application_guidance.dart';

abstract class ApplicationGuidanceRepository {
  Future<ApplicationGuidancePlan> createPlan({
    required String userId,
    required Opportunity opportunity,
    required ApplicantProfile profile,
    required List<UserDocument> documents,
  });
  Future<ApplicationGuidancePlan?> getPlan(String userId, String opportunityId);
  Future<ApplicationGuidancePlan> updateItem(
    String planId,
    String itemId,
    GuidanceItemStatus status,
  );
  Future<ApplicationGuidancePlan> trackRecommendationLetter(
    String planId,
    RecommendationLetterTracker letter,
  );
  Future<ApplicationGuidancePlan> confirmSubmission(
    String planId,
    SubmissionConfirmation confirmation,
  );
}
