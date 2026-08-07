import '../../opportunities/data/demo_opportunity_repository.dart';
import '../../opportunities/domain/opportunity.dart';
import '../domain/collected_opportunity.dart';
import '../domain/opportunity_collection_repository.dart';
import '../../sources/domain/source_registry_repository.dart';

class DemoOpportunityCollectionRepository
    implements OpportunityCollectionRepository {
  DemoOpportunityCollectionRepository(
    this._opportunities, {
    SourceRegistryRepository? sourceRegistry,
    DateTime Function()? clock,
  }) : _sourceRegistry = sourceRegistry,
       _clock = clock ?? DateTime.now;

  final DemoOpportunityRepository _opportunities;
  final DateTime Function() _clock;
  final SourceRegistryRepository? _sourceRegistry;
  final List<CollectedOpportunity> _ledger = [];

  @override
  Future<List<CollectedOpportunity>> getIntakeLedger() async => [..._ledger]
    ..sort((left, right) => right.discoveredAt.compareTo(left.discoveredAt));

  @override
  Future<CollectedOpportunity> collect({
    required Opportunity opportunity,
    required CollectionSourceType sourceType,
    required String sourceLocation,
    required bool automated,
    required bool approvedSource,
    String? collectedByUserId,
  }) async {
    if (sourceLocation.trim().isEmpty) {
      throw const CollectionFailure('Source provenance is required.');
    }
    final registeredSource = automated
        ? await _sourceRegistry?.approvedSourceFor(sourceLocation)
        : null;
    if (automated &&
        (_sourceRegistry != null
            ? registeredSource == null
            : !approvedSource)) {
      throw const CollectionFailure(
        'Automated collection is restricted to approved registry sources.',
      );
    }
    final pending = opportunity.copyWith(
      verificationStatus: VerificationStatus.pending,
      clearLastVerifiedAt: true,
    );
    await _opportunities.ingestCollected(pending);
    final record = CollectedOpportunity(
      id: 'collection-${_clock().microsecondsSinceEpoch}',
      opportunityId: pending.id,
      sourceType: sourceType,
      sourceLocation: sourceLocation.trim(),
      discoveredAt: _clock(),
      collectedByUserId: collectedByUserId,
      automated: automated,
      approvedSource: registeredSource != null || approvedSource,
      verificationStatus: VerificationStatus.pending,
    );
    _ledger.add(record);
    return record;
  }
}
