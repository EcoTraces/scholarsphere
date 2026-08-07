enum GuidanceItemType {
  applicationStep,
  requiredDocument,
  profileInformation,
  curriculumVitae,
  personalStatement,
  researchProposal,
  recommendationLetter,
  interviewPreparation,
  submission,
  followUp,
}

enum GuidanceItemStatus {
  notStarted,
  inProgress,
  ready,
  missing,
  confirmed,
  notApplicable,
}

class GuidanceItem {
  const GuidanceItem({
    required this.id,
    required this.type,
    required this.title,
    required this.guidance,
    required this.status,
    required this.required,
    required this.order,
    this.dueAt,
  });
  final String id;
  final GuidanceItemType type;
  final String title;
  final String guidance;
  final GuidanceItemStatus status;
  final bool required;
  final int order;
  final DateTime? dueAt;

  GuidanceItem copyWith({GuidanceItemStatus? status}) => GuidanceItem(
    id: id,
    type: type,
    title: title,
    guidance: guidance,
    status: status ?? this.status,
    required: required,
    order: order,
    dueAt: dueAt,
  );
}

class RecommendationLetterTracker {
  const RecommendationLetterTracker({
    required this.id,
    required this.refereeName,
    required this.refereeEmail,
    required this.requestedAt,
    required this.dueAt,
    required this.received,
    this.receivedAt,
  });
  final String id;
  final String refereeName;
  final String refereeEmail;
  final DateTime requestedAt;
  final DateTime dueAt;
  final bool received;
  final DateTime? receivedAt;
}

class SubmissionConfirmation {
  const SubmissionConfirmation({
    required this.confirmedAt,
    required this.applicationReference,
    required this.confirmedByUserId,
    required this.officialPortal,
  });
  final DateTime confirmedAt;
  final String applicationReference;
  final String confirmedByUserId;
  final String officialPortal;
}

class ApplicationGuidancePlan {
  const ApplicationGuidancePlan({
    required this.id,
    required this.userId,
    required this.opportunityId,
    required this.items,
    required this.recommendationLetters,
    required this.timelineStart,
    required this.deadline,
    required this.followUpReminders,
    required this.updatedAt,
    this.submissionConfirmation,
  });
  final String id;
  final String userId;
  final String opportunityId;
  final List<GuidanceItem> items;
  final List<RecommendationLetterTracker> recommendationLetters;
  final DateTime timelineStart;
  final DateTime deadline;
  final List<DateTime> followUpReminders;
  final DateTime updatedAt;
  final SubmissionConfirmation? submissionConfirmation;

  int get documentReadinessScore => _score(
    items.where((item) => item.type == GuidanceItemType.requiredDocument),
  );
  int get applicationReadinessScore => _score(
    items.where(
      (item) =>
          item.required &&
          item.type != GuidanceItemType.interviewPreparation &&
          item.type != GuidanceItemType.followUp,
    ),
  );
  List<GuidanceItem> get missingInformation =>
      items.where((item) => item.status == GuidanceItemStatus.missing).toList();

  static int _score(Iterable<GuidanceItem> values) {
    final items = values.toList();
    if (items.isEmpty) return 100;
    final ready = items.where(
      (item) => {
        GuidanceItemStatus.ready,
        GuidanceItemStatus.confirmed,
        GuidanceItemStatus.notApplicable,
      }.contains(item.status),
    );
    return ((ready.length / items.length) * 100).round();
  }

  String get disclaimer =>
      'ScholarSphere can organize and review application materials, but does '
      'not make documents official or guarantee successful selection.';

  ApplicationGuidancePlan copyWith({
    List<GuidanceItem>? items,
    List<RecommendationLetterTracker>? recommendationLetters,
    List<DateTime>? followUpReminders,
    DateTime? updatedAt,
    SubmissionConfirmation? submissionConfirmation,
  }) => ApplicationGuidancePlan(
    id: id,
    userId: userId,
    opportunityId: opportunityId,
    items: items ?? this.items,
    recommendationLetters: recommendationLetters ?? this.recommendationLetters,
    timelineStart: timelineStart,
    deadline: deadline,
    followUpReminders: followUpReminders ?? this.followUpReminders,
    updatedAt: updatedAt ?? this.updatedAt,
    submissionConfirmation:
        submissionConfirmation ?? this.submissionConfirmation,
  );
}
