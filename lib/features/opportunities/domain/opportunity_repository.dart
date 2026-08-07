import 'opportunity.dart';

abstract interface class OpportunityRepository {
  Future<List<Opportunity>> getPublished();

  Future<List<Opportunity>> getForProvider(String providerId);

  Future<void> submit({
    required String providerId,
    required Opportunity opportunity,
  });

  Future<List<Opportunity>> getAllForAdministration();
}
