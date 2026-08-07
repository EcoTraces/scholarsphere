enum LegalPolicyType {
  termsAndConditions,
  privacyPolicy,
  cookiePolicy,
  acceptableUse,
  providerAgreement,
  contentPublishing,
  verificationDisclaimer,
  fundingDisclaimer,
  copyrightPolicy,
  dataProcessingAgreement,
}

class LegalPolicy {
  const LegalPolicy({
    required this.id,
    required this.type,
    required this.version,
    required this.title,
    required this.content,
    required this.effectiveAt,
    required this.publishedAt,
    required this.requiresAcceptance,
    required this.materialChange,
    required this.publishedBy,
  });
  final String id;
  final LegalPolicyType type;
  final String version;
  final String title;
  final String content;
  final DateTime effectiveAt;
  final DateTime publishedAt;
  final bool requiresAcceptance;
  final bool materialChange;
  final String publishedBy;
}

class PolicyAcceptance {
  const PolicyAcceptance({
    required this.userId,
    required this.policyId,
    required this.policyVersion,
    required this.acceptedAt,
    required this.ipAddress,
  });
  final String userId;
  final String policyId;
  final String policyVersion;
  final DateTime acceptedAt;
  final String ipAddress;
}

enum LegalRequestType {
  takedown,
  complaint,
  regulator,
  courtOrder,
  dataProtection,
}

enum LegalRequestStatus {
  submitted,
  validated,
  inReview,
  actioned,
  rejected,
  closed,
}

class LegalRequest {
  const LegalRequest({
    required this.id,
    required this.type,
    required this.requester,
    required this.subjectEntityId,
    required this.description,
    required this.evidenceLocations,
    required this.status,
    required this.createdAt,
    required this.history,
  });
  final String id;
  final LegalRequestType type;
  final String requester;
  final String subjectEntityId;
  final String description;
  final List<String> evidenceLocations;
  final LegalRequestStatus status;
  final DateTime createdAt;
  final List<String> history;
}

class ComplianceRecord {
  const ComplianceRecord({
    required this.id,
    required this.framework,
    required this.obligation,
    required this.status,
    required this.owner,
    required this.reviewDueAt,
    required this.evidenceLocations,
  });
  final String id;
  final String framework;
  final String obligation;
  final String status;
  final String owner;
  final DateTime reviewDueAt;
  final List<String> evidenceLocations;
}

abstract final class RequiredLegalDisclaimers {
  static const noGuarantee =
      'ScholarSphere does not guarantee admission, funding, selection, visas, or travel approval.';
  static const officialSource =
      'Applicants must confirm all requirements on the official source.';
  static const detailsMayChange =
      'Opportunity details can change after verification.';
  static const sponsored =
      'Sponsored listings are clearly identified as sponsored opportunities.';
  static const unofficialPayments =
      'Do not pay unofficial agents through ScholarSphere.';
}
