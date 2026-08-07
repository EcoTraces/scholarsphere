import '../../opportunities/domain/opportunity.dart';

enum SourceAuthority {
  officialInstitution,
  government,
  embassy,
  officialSponsor,
  internationalOrganization,
  unverifiedThirdParty,
}

enum VerificationWorkflowStatus {
  unreviewed,
  assigned,
  underReview,
  additionalEvidenceRequired,
  awaitingSecondApproval,
  verified,
  conditionallyVerified,
  reverificationRequired,
  verificationExpired,
  rejected,
  suspicious,
  archived,
}

class VerificationChecklist {
  const VerificationChecklist({
    this.officialWebsiteChecked = false,
    this.sponsorConfirmed = false,
    this.applicationLinkTested = false,
    this.deadlineConfirmed = false,
    this.requirementsReviewed = false,
    this.duplicatesChecked = false,
    this.organizationExists = false,
    this.applicationOpen = false,
    this.fundingConfirmed = false,
    this.feesConfirmed = false,
    this.contactDetailsConfirmed = false,
    this.noMisleadingClaims = false,
    this.supportingEvidenceStored = false,
  });

  final bool officialWebsiteChecked;
  final bool sponsorConfirmed;
  final bool applicationLinkTested;
  final bool deadlineConfirmed;
  final bool requirementsReviewed;
  final bool duplicatesChecked;
  final bool organizationExists;
  final bool applicationOpen;
  final bool fundingConfirmed;
  final bool feesConfirmed;
  final bool contactDetailsConfirmed;
  final bool noMisleadingClaims;
  final bool supportingEvidenceStored;

  bool get allPassed =>
      officialWebsiteChecked &&
      sponsorConfirmed &&
      applicationLinkTested &&
      deadlineConfirmed &&
      requirementsReviewed &&
      duplicatesChecked &&
      organizationExists &&
      applicationOpen &&
      fundingConfirmed &&
      feesConfirmed &&
      contactDetailsConfirmed &&
      noMisleadingClaims &&
      supportingEvidenceStored;

  // Kept for compatibility with reviews created before the detailed workflow.
  bool get legacyPassed =>
      officialWebsiteChecked &&
      sponsorConfirmed &&
      applicationLinkTested &&
      deadlineConfirmed &&
      requirementsReviewed &&
      duplicatesChecked;

  VerificationChecklist copyWith({
    bool? officialWebsiteChecked,
    bool? sponsorConfirmed,
    bool? applicationLinkTested,
    bool? deadlineConfirmed,
    bool? requirementsReviewed,
    bool? duplicatesChecked,
    bool? organizationExists,
    bool? applicationOpen,
    bool? fundingConfirmed,
    bool? feesConfirmed,
    bool? contactDetailsConfirmed,
    bool? noMisleadingClaims,
    bool? supportingEvidenceStored,
  }) => VerificationChecklist(
    officialWebsiteChecked:
        officialWebsiteChecked ?? this.officialWebsiteChecked,
    sponsorConfirmed: sponsorConfirmed ?? this.sponsorConfirmed,
    applicationLinkTested: applicationLinkTested ?? this.applicationLinkTested,
    deadlineConfirmed: deadlineConfirmed ?? this.deadlineConfirmed,
    requirementsReviewed: requirementsReviewed ?? this.requirementsReviewed,
    duplicatesChecked: duplicatesChecked ?? this.duplicatesChecked,
    organizationExists: organizationExists ?? this.organizationExists,
    applicationOpen: applicationOpen ?? this.applicationOpen,
    fundingConfirmed: fundingConfirmed ?? this.fundingConfirmed,
    feesConfirmed: feesConfirmed ?? this.feesConfirmed,
    contactDetailsConfirmed:
        contactDetailsConfirmed ?? this.contactDetailsConfirmed,
    noMisleadingClaims: noMisleadingClaims ?? this.noMisleadingClaims,
    supportingEvidenceStored:
        supportingEvidenceStored ?? this.supportingEvidenceStored,
  );
}

class VerificationReview {
  const VerificationReview({
    required this.opportunityId,
    required this.sourceAuthority,
    required this.checklist,
    required this.status,
    required this.notes,
    required this.reviewedByUserId,
    required this.reviewedAt,
    required this.nextReviewAt,
    this.verificationId,
    this.assignedToUserId,
    this.approvedByUserId,
    this.workflowStatus = VerificationWorkflowStatus.underReview,
    this.officialSourceUrl,
    this.evidenceLocation,
    this.expiresAt,
    this.previousStatus,
    this.isCorrection = false,
    this.appealReason,
  });

  final String opportunityId;
  final SourceAuthority sourceAuthority;
  final VerificationChecklist checklist;
  final VerificationStatus status;
  final String notes;
  final String reviewedByUserId;
  final DateTime reviewedAt;
  final DateTime? nextReviewAt;
  final String? verificationId;
  final String? assignedToUserId;
  final String? approvedByUserId;
  final VerificationWorkflowStatus workflowStatus;
  final String? officialSourceUrl;
  final String? evidenceLocation;
  final DateTime? expiresAt;
  final VerificationWorkflowStatus? previousStatus;
  final bool isCorrection;
  final String? appealReason;

  bool get hasOfficialAuthority =>
      sourceAuthority != SourceAuthority.unverifiedThirdParty;

  VerificationReview copyWith({
    VerificationStatus? status,
    String? approvedByUserId,
    VerificationWorkflowStatus? workflowStatus,
    DateTime? reviewedAt,
    DateTime? expiresAt,
    DateTime? nextReviewAt,
  }) => VerificationReview(
    opportunityId: opportunityId,
    sourceAuthority: sourceAuthority,
    checklist: checklist,
    status: status ?? this.status,
    notes: notes,
    reviewedByUserId: reviewedByUserId,
    reviewedAt: reviewedAt ?? this.reviewedAt,
    nextReviewAt: nextReviewAt ?? this.nextReviewAt,
    verificationId: verificationId,
    assignedToUserId: assignedToUserId,
    approvedByUserId: approvedByUserId ?? this.approvedByUserId,
    workflowStatus: workflowStatus ?? this.workflowStatus,
    officialSourceUrl: officialSourceUrl,
    evidenceLocation: evidenceLocation,
    expiresAt: expiresAt ?? this.expiresAt,
    previousStatus: previousStatus,
    isCorrection: isCorrection,
    appealReason: appealReason,
  );
}

class VerificationFailure implements Exception {
  const VerificationFailure(this.message);

  final String message;
}
