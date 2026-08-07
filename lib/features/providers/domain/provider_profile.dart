enum ProviderStatus {
  draft,
  pendingReview,
  additionalInformationRequired,
  verified,
  rejected,
  suspended,
  verificationExpired,
  archived,
}

enum ProviderPermission {
  manageOrganization,
  publishOpportunities,
  manageAdmins,
}

enum ProviderRiskLevel { low, medium, high }

class ProviderAdministrator {
  const ProviderAdministrator({
    required this.userId,
    required this.email,
    required this.permissions,
  });
  final String userId;
  final String email;
  final Set<ProviderPermission> permissions;
}

class ProviderActivity {
  const ProviderActivity({
    required this.action,
    required this.actorId,
    required this.occurredAt,
  });
  final String action;
  final String actorId;
  final DateTime occurredAt;
}

class ProviderAppeal {
  const ProviderAppeal({
    required this.reason,
    required this.submittedAt,
    required this.status,
  });
  final String reason;
  final DateTime submittedAt;
  final String status;
}

class ProviderProfile {
  const ProviderProfile({
    required this.id,
    required this.ownerUserId,
    required this.organizationName,
    required this.organizationType,
    required this.registrationNumber,
    required this.country,
    required this.officialWebsite,
    required this.officialEmailDomain,
    required this.physicalAddress,
    required this.contactPerson,
    required this.contactPhone,
    required this.supportingDocuments,
    required this.socialMediaLinks,
    required this.status,
    required this.riskScore,
    required this.permissions,
    this.administrators = const [],
    this.activityHistory = const [],
    this.appeals = const [],
    this.verificationDate,
    this.verifiedBy,
    this.reverificationDate,
    this.reviewNote,
  });

  final String id;
  final String ownerUserId;
  final String organizationName;
  final String organizationType;
  final String registrationNumber;
  final String country;
  final String officialWebsite;
  final String officialEmailDomain;
  final String physicalAddress;
  final String contactPerson;
  final String contactPhone;
  final List<String> supportingDocuments;
  final List<String> socialMediaLinks;
  final ProviderStatus status;
  final int riskScore;
  final Set<ProviderPermission> permissions;
  final List<ProviderAdministrator> administrators;
  final List<ProviderActivity> activityHistory;
  final List<ProviderAppeal> appeals;
  final DateTime? verificationDate;
  final String? verifiedBy;
  final DateTime? reverificationDate;
  final String? reviewNote;

  bool get hasVerifiedBadge =>
      status == ProviderStatus.verified &&
      (reverificationDate == null ||
          reverificationDate!.isAfter(DateTime.now()));

  ProviderRiskLevel get riskLevel => riskScore >= 70
      ? ProviderRiskLevel.high
      : riskScore >= 35
      ? ProviderRiskLevel.medium
      : ProviderRiskLevel.low;

  ProviderProfile copyWith({
    ProviderStatus? status,
    int? riskScore,
    Set<ProviderPermission>? permissions,
    List<ProviderAdministrator>? administrators,
    List<ProviderActivity>? activityHistory,
    List<ProviderAppeal>? appeals,
    DateTime? verificationDate,
    String? verifiedBy,
    DateTime? reverificationDate,
    String? reviewNote,
  }) => ProviderProfile(
    id: id,
    ownerUserId: ownerUserId,
    organizationName: organizationName,
    organizationType: organizationType,
    registrationNumber: registrationNumber,
    country: country,
    officialWebsite: officialWebsite,
    officialEmailDomain: officialEmailDomain,
    physicalAddress: physicalAddress,
    contactPerson: contactPerson,
    contactPhone: contactPhone,
    supportingDocuments: supportingDocuments,
    socialMediaLinks: socialMediaLinks,
    status: status ?? this.status,
    riskScore: riskScore ?? this.riskScore,
    permissions: permissions ?? this.permissions,
    administrators: administrators ?? this.administrators,
    activityHistory: activityHistory ?? this.activityHistory,
    appeals: appeals ?? this.appeals,
    verificationDate: verificationDate ?? this.verificationDate,
    verifiedBy: verifiedBy ?? this.verifiedBy,
    reverificationDate: reverificationDate ?? this.reverificationDate,
    reviewNote: reviewNote ?? this.reviewNote,
  );
}

class ProviderReviewChecklist {
  const ProviderReviewChecklist({
    required this.officialEmailVerified,
    required this.domainVerified,
    required this.contactVerified,
    required this.documentsVerified,
    required this.impersonationCheckPassed,
  });

  final bool officialEmailVerified;
  final bool domainVerified;
  final bool contactVerified;
  final bool documentsVerified;
  final bool impersonationCheckPassed;

  bool get complete =>
      officialEmailVerified &&
      domainVerified &&
      contactVerified &&
      documentsVerified &&
      impersonationCheckPassed;
}
