import '../../opportunities/domain/opportunity.dart';

enum ApplicationStage {
  interested,
  saved,
  preparingDocuments,
  applicationStarted,
  applicationSubmitted,
  interviewStage,
  waitingForDecision,
  accepted,
  rejected,
  withdrawn,
}

class ApplicationRecord {
  const ApplicationRecord({
    required this.id,
    required this.userId,
    required this.opportunityId,
    required this.opportunityTitle,
    required this.provider,
    required this.deadline,
    required this.stage,
    required this.createdAt,
    required this.updatedAt,
    required this.missingDocuments,
    required this.personalNotes,
    required this.followUpActions,
    this.applicationDate,
    this.applicationReferenceNumber,
    this.interviewDate,
    this.resultDate,
    this.scholarshipValue,
  });

  factory ApplicationRecord.saved({
    required String userId,
    required Opportunity opportunity,
    required DateTime now,
  }) => ApplicationRecord(
    id: '$userId-${opportunity.id}',
    userId: userId,
    opportunityId: opportunity.id,
    opportunityTitle: opportunity.title,
    provider: opportunity.provider,
    deadline: opportunity.deadline,
    stage: ApplicationStage.saved,
    createdAt: now,
    updatedAt: now,
    missingDocuments: const [],
    personalNotes: '',
    followUpActions: const [],
  );

  final String id;
  final String userId;
  final String opportunityId;
  final String opportunityTitle;
  final String provider;
  final DateTime deadline;
  final ApplicationStage stage;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? applicationDate;
  final String? applicationReferenceNumber;
  final List<String> missingDocuments;
  final DateTime? interviewDate;
  final String personalNotes;
  final DateTime? resultDate;
  final double? scholarshipValue;
  final List<String> followUpActions;

  ApplicationRecord copyWith({
    ApplicationStage? stage,
    DateTime? updatedAt,
    DateTime? applicationDate,
    String? applicationReferenceNumber,
    List<String>? missingDocuments,
    DateTime? interviewDate,
    String? personalNotes,
    DateTime? resultDate,
    double? scholarshipValue,
    List<String>? followUpActions,
  }) => ApplicationRecord(
    id: id,
    userId: userId,
    opportunityId: opportunityId,
    opportunityTitle: opportunityTitle,
    provider: provider,
    deadline: deadline,
    stage: stage ?? this.stage,
    createdAt: createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    applicationDate: applicationDate ?? this.applicationDate,
    applicationReferenceNumber:
        applicationReferenceNumber ?? this.applicationReferenceNumber,
    missingDocuments: missingDocuments ?? this.missingDocuments,
    interviewDate: interviewDate ?? this.interviewDate,
    personalNotes: personalNotes ?? this.personalNotes,
    resultDate: resultDate ?? this.resultDate,
    scholarshipValue: scholarshipValue ?? this.scholarshipValue,
    followUpActions: followUpActions ?? this.followUpActions,
  );

  String get stageLabel => switch (stage) {
    ApplicationStage.interested => 'Interested',
    ApplicationStage.saved => 'Saved',
    ApplicationStage.preparingDocuments => 'Preparing documents',
    ApplicationStage.applicationStarted => 'Application started',
    ApplicationStage.applicationSubmitted => 'Application submitted',
    ApplicationStage.interviewStage => 'Interview stage',
    ApplicationStage.waitingForDecision => 'Waiting for decision',
    ApplicationStage.accepted => 'Accepted',
    ApplicationStage.rejected => 'Rejected',
    ApplicationStage.withdrawn => 'Withdrawn',
  };
}
