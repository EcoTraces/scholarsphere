enum ConsentType {
  privacyPolicy,
  termsAndConditions,
  cookies,
  marketing,
  notifications,
  personalizedRecommendations,
  sensitiveData,
  documentStorage,
  thirdPartySharing,
}

enum PrivacyRequestType {
  dataExport,
  accountDeletion,
  dataCorrection,
  documentDeletion,
}

enum PrivacyRequestStatus {
  submitted,
  inReview,
  completed,
  rejected,
  cancelled,
}

class ConsentRecord {
  const ConsentRecord({
    required this.userId,
    required this.type,
    required this.policyVersion,
    required this.grantedAt,
    required this.withdrawnAt,
  });

  final String userId;
  final ConsentType type;
  final String policyVersion;
  final DateTime grantedAt;
  final DateTime? withdrawnAt;

  bool get isActive => withdrawnAt == null;

  ConsentRecord withdraw(DateTime at) => ConsentRecord(
    userId: userId,
    type: type,
    policyVersion: policyVersion,
    grantedAt: grantedAt,
    withdrawnAt: at,
  );
}

class PrivacyRequest {
  const PrivacyRequest({
    required this.id,
    required this.userId,
    required this.type,
    required this.status,
    required this.submittedAt,
    required this.completedAt,
    required this.notes,
  });

  final String id;
  final String userId;
  final PrivacyRequestType type;
  final PrivacyRequestStatus status;
  final DateTime submittedAt;
  final DateTime? completedAt;
  final String notes;
}

class OrganizationAccessRecord {
  const OrganizationAccessRecord({
    required this.id,
    required this.userId,
    required this.organizationId,
    required this.organizationName,
    required this.dataCategories,
    required this.accessedAt,
    required this.consentRecordType,
  });

  final String id;
  final String userId;
  final String organizationId;
  final String organizationName;
  final Set<String> dataCategories;
  final DateTime accessedAt;
  final ConsentType consentRecordType;
}

class PrivacyIncident {
  const PrivacyIncident({
    required this.id,
    required this.recordedAt,
    required this.summary,
    required this.affectedUserIds,
    required this.resolvedAt,
  });

  final String id;
  final DateTime recordedAt;
  final String summary;
  final Set<String> affectedUserIds;
  final DateTime? resolvedAt;
}

class PrivacyFailure implements Exception {
  const PrivacyFailure(this.message);

  final String message;
}
