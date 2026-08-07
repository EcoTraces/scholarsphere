import '../../opportunities/domain/opportunity.dart';
import 'collected_opportunity.dart';

abstract interface class OpportunityCollectionRepository {
  Future<List<CollectedOpportunity>> getIntakeLedger();

  Future<CollectedOpportunity> collect({
    required Opportunity opportunity,
    required CollectionSourceType sourceType,
    required String sourceLocation,
    required bool automated,
    required bool approvedSource,
    String? collectedByUserId,
  });
}
