enum OpportunitySourceType {
  officialUniversityWebsite,
  officialGovernmentPortal,
  embassyWebsite,
  foundationWebsite,
  internationalOrganization,
  officialApplicationPortal,
  approvedApi,
  approvedRssFeed,
  verifiedProviderSubmission,
  trustedSecondarySource,
  communitySubmission,
}

enum ReliabilityLevel { a, b, c, d, e, f }

enum SourceVerificationStatus { pending, approved, blocked, expired }

class SourceRecord {
  const SourceRecord({
    required this.id,
    required this.name,
    required this.type,
    required this.domain,
    required this.country,
    required this.organizationId,
    required this.trustLevel,
    required this.trustScore,
    required this.verificationStatus,
    required this.accuracyRate,
    required this.correctionCount,
    required this.rejectionCount,
    required this.isBlocked,
    required this.createdAt,
    required this.updatedAt,
    this.lastCheckedAt,
    this.lastSuccessfulAccess,
    this.expiresAt,
    this.parserConfiguration,
  });

  final String id;
  final String name;
  final OpportunitySourceType type;
  final String domain;
  final String country;
  final String organizationId;
  final ReliabilityLevel trustLevel;
  final int trustScore;
  final SourceVerificationStatus verificationStatus;
  final DateTime? lastCheckedAt;
  final DateTime? lastSuccessfulAccess;
  final double accuracyRate;
  final int correctionCount;
  final int rejectionCount;
  final bool isBlocked;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? expiresAt;
  final Map<String, String>? parserConfiguration;

  bool get isApproved =>
      verificationStatus == SourceVerificationStatus.approved &&
      !isBlocked &&
      (expiresAt == null || expiresAt!.isAfter(DateTime.now()));

  SourceRecord copyWith({
    ReliabilityLevel? trustLevel,
    int? trustScore,
    SourceVerificationStatus? verificationStatus,
    DateTime? lastCheckedAt,
    DateTime? lastSuccessfulAccess,
    double? accuracyRate,
    int? correctionCount,
    int? rejectionCount,
    bool? isBlocked,
    DateTime? updatedAt,
    DateTime? expiresAt,
  }) => SourceRecord(
    id: id,
    name: name,
    type: type,
    domain: domain,
    country: country,
    organizationId: organizationId,
    trustLevel: trustLevel ?? this.trustLevel,
    trustScore: trustScore ?? this.trustScore,
    verificationStatus: verificationStatus ?? this.verificationStatus,
    lastCheckedAt: lastCheckedAt ?? this.lastCheckedAt,
    lastSuccessfulAccess: lastSuccessfulAccess ?? this.lastSuccessfulAccess,
    accuracyRate: accuracyRate ?? this.accuracyRate,
    correctionCount: correctionCount ?? this.correctionCount,
    rejectionCount: rejectionCount ?? this.rejectionCount,
    isBlocked: isBlocked ?? this.isBlocked,
    createdAt: createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    expiresAt: expiresAt ?? this.expiresAt,
    parserConfiguration: parserConfiguration,
  );
}
