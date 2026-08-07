import '../../opportunities/domain/opportunity.dart';

enum CollectionSourceType {
  manualAdministrator,
  providerSubmission,
  officialApi,
  approvedRss,
  structuredFeed,
  controlledWebCollection,
  userSubmission,
}

class CollectedOpportunity {
  const CollectedOpportunity({
    required this.id,
    required this.opportunityId,
    required this.sourceType,
    required this.sourceLocation,
    required this.discoveredAt,
    required this.collectedByUserId,
    required this.automated,
    required this.approvedSource,
    required this.verificationStatus,
  });

  final String id;
  final String opportunityId;
  final CollectionSourceType sourceType;
  final String sourceLocation;
  final DateTime discoveredAt;
  final String? collectedByUserId;
  final bool automated;
  final bool approvedSource;
  final VerificationStatus verificationStatus;
}

class CollectionFailure implements Exception {
  const CollectionFailure(this.message);

  final String message;
}
