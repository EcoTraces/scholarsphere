import '../../documents/domain/document_readiness.dart';
import '../../opportunities/domain/opportunity.dart';
import '../../profiles/domain/applicant_profile.dart';
import '../domain/application_guidance.dart';
import '../domain/application_guidance_repository.dart';

class DemoApplicationGuidanceRepository
    implements ApplicationGuidanceRepository {
  DemoApplicationGuidanceRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final Map<String, ApplicationGuidancePlan> _plans = {};

  @override
  Future<ApplicationGuidancePlan> createPlan({
    required String userId,
    required Opportunity opportunity,
    required ApplicantProfile profile,
    required List<UserDocument> documents,
  }) async {
    final available = documents.map((document) => document.type).toSet();
    final items = <GuidanceItem>[];
    var order = 0;
    for (final requirement in opportunity.requiredDocuments) {
      final type = DocumentTypes.fromRequirement(requirement);
      items.add(
        GuidanceItem(
          id: 'document-${order++}',
          type: GuidanceItemType.requiredDocument,
          title: requirement,
          guidance: 'Prepare the requested document and verify its format.',
          status: type != null && available.contains(type)
              ? GuidanceItemStatus.ready
              : GuidanceItemStatus.missing,
          required: true,
          order: order,
          dueAt: opportunity.deadline.subtract(const Duration(days: 7)),
        ),
      );
    }
    for (final step in opportunity.applicationProcedure) {
      items.add(
        GuidanceItem(
          id: 'step-${order++}',
          type: GuidanceItemType.applicationStep,
          title: step,
          guidance: 'Complete this step on the official application portal.',
          status: GuidanceItemStatus.notStarted,
          required: true,
          order: order,
          dueAt: opportunity.deadline,
        ),
      );
    }
    final missingProfile = <String>[
      if (profile.nationality.isEmpty) 'Nationality',
      if (profile.highestQualification.isEmpty) 'Highest qualification',
      if (profile.degreeField.isEmpty) 'Academic field',
    ];
    for (final field in missingProfile) {
      items.add(
        GuidanceItem(
          id: 'profile-${order++}',
          type: GuidanceItemType.profileInformation,
          title: field,
          guidance: 'Complete this information in your private profile.',
          status: GuidanceItemStatus.missing,
          required: true,
          order: order,
        ),
      );
    }
    items.addAll([
      GuidanceItem(
        id: 'cv',
        type: GuidanceItemType.curriculumVitae,
        title: 'CV readiness review',
        guidance:
            'Check accuracy, dates, relevance, and consistent formatting.',
        status: available.contains(DocumentType.curriculumVitae)
            ? GuidanceItemStatus.inProgress
            : GuidanceItemStatus.missing,
        required: opportunity.requiredDocuments.any(
          (value) =>
              DocumentTypes.fromRequirement(value) ==
              DocumentType.curriculumVitae,
        ),
        order: order++,
      ),
      GuidanceItem(
        id: 'interview',
        type: GuidanceItemType.interviewPreparation,
        title: 'Interview preparation',
        guidance: 'Review the program, prepare evidence-based examples, and test your setup.',
        status: GuidanceItemStatus.notStarted,
        required: false,
        order: order++,
      ),
    ]);
    final now = _clock();
    final plan = ApplicationGuidancePlan(
      id: '$userId-${opportunity.id}',
      userId: userId,
      opportunityId: opportunity.id,
      items: items,
      recommendationLetters: const [],
      timelineStart: now,
      deadline: opportunity.deadline,
      followUpReminders: [
        opportunity.deadline.add(const Duration(days: 7)),
        opportunity.deadline.add(const Duration(days: 30)),
      ],
      updatedAt: now,
    );
    _plans[plan.id] = plan;
    return plan;
  }

  @override
  Future<ApplicationGuidancePlan?> getPlan(
    String userId,
    String opportunityId,
  ) async => _plans['$userId-$opportunityId'];

  @override
  Future<ApplicationGuidancePlan> updateItem(
    String planId,
    String itemId,
    GuidanceItemStatus status,
  ) async {
    final plan = _require(planId);
    final updated = plan.copyWith(
      items: plan.items
          .map(
            (item) => item.id == itemId ? item.copyWith(status: status) : item,
          )
          .toList(),
      updatedAt: _clock(),
    );
    _plans[planId] = updated;
    return updated;
  }

  @override
  Future<ApplicationGuidancePlan> trackRecommendationLetter(
    String planId,
    RecommendationLetterTracker letter,
  ) async {
    final plan = _require(planId);
    final updated = plan.copyWith(
      recommendationLetters: [...plan.recommendationLetters, letter],
      updatedAt: _clock(),
    );
    _plans[planId] = updated;
    return updated;
  }

  @override
  Future<ApplicationGuidancePlan> confirmSubmission(
    String planId,
    SubmissionConfirmation confirmation,
  ) async {
    final plan = _require(planId);
    if (confirmation.applicationReference.trim().isEmpty ||
        confirmation.officialPortal.trim().isEmpty) {
      throw StateError(
        'Submission confirmation requires an official portal and reference.',
      );
    }
    final updated = plan.copyWith(
      submissionConfirmation: confirmation,
      updatedAt: _clock(),
    );
    _plans[planId] = updated;
    return updated;
  }

  ApplicationGuidancePlan _require(String id) {
    final value = _plans[id];
    if (value == null) throw StateError('Guidance plan was not found.');
    return value;
  }
}
