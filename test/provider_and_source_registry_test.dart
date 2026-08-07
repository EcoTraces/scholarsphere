import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/providers/data/demo_provider_repository.dart';
import 'package:scholarsphere/features/providers/domain/provider_profile.dart';
import 'package:scholarsphere/features/providers/domain/provider_repository.dart';
import 'package:scholarsphere/features/sources/data/demo_source_registry_repository.dart';
import 'package:scholarsphere/features/sources/domain/source_record.dart';
import 'package:scholarsphere/features/sources/domain/source_registry_repository.dart';

void main() {
  test(
    'provider cannot publish until every verification check passes',
    () async {
      final repository = DemoProviderRepository(
        clock: () => DateTime.utc(2026, 7, 29),
      );
      final provider = await repository.register(_provider());

      expect(await repository.canPublish('owner-1'), isFalse);
      await expectLater(
        repository.review(
          providerId: provider.id,
          officerId: 'officer-1',
          decision: ProviderStatus.verified,
          checklist: const ProviderReviewChecklist(
            officialEmailVerified: true,
            domainVerified: true,
            contactVerified: true,
            documentsVerified: true,
            impersonationCheckPassed: false,
          ),
        ),
        throwsA(isA<ProviderFailure>()),
      );

      await repository.review(
        providerId: provider.id,
        officerId: 'officer-1',
        decision: ProviderStatus.verified,
        checklist: const ProviderReviewChecklist(
          officialEmailVerified: true,
          domainVerified: true,
          contactVerified: true,
          documentsVerified: true,
          impersonationCheckPassed: true,
        ),
      );
      expect(await repository.canPublish('owner-1'), isTrue);

      await repository.suspend(provider.id, 'Security review');
      expect(await repository.canPublish('owner-1'), isFalse);
    },
  );

  test(
    'source registry rejects duplicates and only returns approved sources',
    () async {
      final repository = DemoSourceRegistryRepository();
      final source = await repository.register(_source());
      expect(
        await repository.approvedSourceFor('https://example.edu/a'),
        isNull,
      );

      await repository.review(
        sourceId: source.id,
        trustLevel: ReliabilityLevel.a,
        status: SourceVerificationStatus.approved,
      );
      expect(
        await repository.approvedSourceFor('https://apply.example.edu/a'),
        isNotNull,
      );

      await expectLater(
        repository.register(_source(id: 'source-2')),
        throwsA(isA<SourceRegistryFailure>()),
      );
    },
  );
}

ProviderProfile _provider() => const ProviderProfile(
  id: 'provider-1',
  ownerUserId: 'owner-1',
  organizationName: 'Example University',
  organizationType: 'University',
  registrationNumber: 'REG-1',
  country: 'Ghana',
  officialWebsite: 'https://example.edu',
  officialEmailDomain: 'example.edu',
  physicalAddress: '1 University Road',
  contactPerson: 'Admissions Office',
  contactPhone: '+233000000000',
  supportingDocuments: ['registration.pdf'],
  socialMediaLinks: [],
  status: ProviderStatus.draft,
  riskScore: 0,
  permissions: {},
);

SourceRecord _source({String id = 'source-1'}) {
  final now = DateTime.utc(2026, 7, 29);
  return SourceRecord(
    id: id,
    name: 'Example University',
    type: OpportunitySourceType.officialUniversityWebsite,
    domain: 'example.edu',
    country: 'Ghana',
    organizationId: 'provider-1',
    trustLevel: ReliabilityLevel.e,
    trustScore: 0,
    verificationStatus: SourceVerificationStatus.pending,
    accuracyRate: 1,
    correctionCount: 0,
    rejectionCount: 0,
    isBlocked: false,
    createdAt: now,
    updatedAt: now,
  );
}
