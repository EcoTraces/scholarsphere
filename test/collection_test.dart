import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/collection/data/demo_opportunity_collection_repository.dart';
import 'package:scholarsphere/features/collection/domain/collected_opportunity.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/opportunities/domain/opportunity.dart';

void main() {
  test(
    'automated collection requires approval and stays unpublished',
    () async {
      final opportunities = DemoOpportunityRepository();
      final source = (await opportunities.getPublished()).first.copyWith(
        id: 'new-api-record',
      );
      final collection = DemoOpportunityCollectionRepository(
        opportunities,
        clock: () => DateTime(2026, 7, 28),
      );

      await expectLater(
        collection.collect(
          opportunity: source,
          sourceType: CollectionSourceType.officialApi,
          sourceLocation: 'https://official.example/api',
          automated: true,
          approvedSource: false,
        ),
        throwsA(isA<CollectionFailure>()),
      );

      final record = await collection.collect(
        opportunity: source,
        sourceType: CollectionSourceType.officialApi,
        sourceLocation: 'https://official.example/api',
        automated: true,
        approvedSource: true,
      );
      final published = await opportunities.getPublished();
      final verificationQueue = await opportunities.getVerificationCandidates();

      expect(record.verificationStatus, VerificationStatus.pending);
      expect(published.any((item) => item.id == source.id), isFalse);
      expect(verificationQueue.any((item) => item.id == source.id), isTrue);
    },
  );
}
