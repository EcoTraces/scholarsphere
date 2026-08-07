import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/data_transfer/data/demo_data_transfer_repository.dart';
import 'package:scholarsphere/features/data_transfer/domain/data_transfer.dart';
import 'package:scholarsphere/features/platforms/data/demo_platform_management_repository.dart';
import 'package:scholarsphere/features/platforms/domain/platform_management.dart';
import 'package:scholarsphere/features/provider_analytics/data/demo_provider_analytics_repository.dart';
import 'package:scholarsphere/features/provider_analytics/domain/provider_analytics.dart';

void main() {
  test('provider analytics suppress dimensions for small cohorts', () async {
    final analytics = DemoProviderAnalyticsRepository(minimumCohortSize: 3);
    for (var index = 0; index < 2; index++) {
      await analytics.record(
        EngagementEvent(
          providerId: 'provider-1',
          opportunityId: 'opportunity-1',
          kind: 'view',
          country: 'Ghana',
          studyLevel: 'Masters',
          field: 'Computing',
          occurredAt: DateTime.utc(2026, 7, 29),
          userId: 'user-$index',
        ),
      );
    }

    var snapshot = await analytics.snapshot('provider-1');
    expect(snapshot.views, 2);
    expect(snapshot.suppressed, isTrue);
    expect(snapshot.countries, isEmpty);

    await analytics.record(
      EngagementEvent(
        providerId: 'provider-1',
        opportunityId: 'opportunity-1',
        kind: 'save',
        country: 'Kenya',
        studyLevel: 'PhD',
        field: 'Engineering',
        occurredAt: DateTime.utc(2026, 7, 29),
        userId: 'user-3',
      ),
    );
    snapshot = await analytics.snapshot('provider-1');
    expect(snapshot.suppressed, isFalse);
    expect(snapshot.countries, {'Ghana': 2, 'Kenya': 1});
  });

  test(
    'imports require preview and approval before verification queue',
    () async {
      final transfers = DemoDataTransferRepository();
      final batch = await transfers.upload(
        format: ImportFormat.csv,
        actorId: 'provider-1',
        records: const [
          {
            'title': 'Research Scholarship',
            'officialSourceUrl': 'https://university.example/scholarship',
          },
        ],
      );
      expect(
        () => transfers.importToVerificationQueue(batch.id),
        throwsStateError,
      );

      final preview = await transfers.preview(batch.id);
      expect(preview.status, ImportStatus.previewed);
      await transfers.approve(batch.id, 'administrator-1');
      final imported = await transfers.importToVerificationQueue(batch.id);
      expect(imported.status, ImportStatus.imported);
      await transfers.rollback(batch.id, 'administrator-1');
      expect((await transfers.auditLog()).last, contains('rolled back'));
    },
  );

  test('invalid import rows cannot be approved', () async {
    final transfers = DemoDataTransferRepository();
    final batch = await transfers.upload(
      format: ImportFormat.json,
      actorId: 'provider-1',
      records: const [
        {'title': 'Missing source'},
      ],
    );
    await transfers.preview(batch.id);
    expect(
      () => transfers.approve(batch.id, 'administrator-1'),
      throwsStateError,
    );
  });

  test('mobile policies enforce critical updates and revoke tokens', () async {
    final mobile = DemoMobileManagementRepository(const [
      MobileReleasePolicy(
        platform: 'android',
        minimumVersion: 120,
        latestVersion: 125,
        forceCriticalUpdate: true,
      ),
    ]);
    expect(await mobile.requiresUpdate('android', 119), isTrue);
    expect(await mobile.requiresUpdate('android', 120), isFalse);

    await mobile.registerDevice(
      MobileDevice(
        id: 'device-1',
        userId: 'user-1',
        platform: 'android',
        pushToken: 'encrypted-token-reference',
        biometricEnabled: true,
        lowDataMode: true,
        lastSyncAt: DateTime.utc(2026, 7, 29),
      ),
    );
    expect(await mobile.devicesFor('user-1'), hasLength(1));
    await mobile.revokeToken('device-1');
    expect(await mobile.devicesFor('user-1'), isEmpty);
  });

  test('public sitemap excludes private and non-indexable pages', () async {
    final portal = DemoPublicPortalRepository();
    await portal.publish(
      const PublicPageMetadata(
        path: '/opportunities/research-scholarship',
        title: 'Research Scholarship',
        description: 'Verified scholarship opportunity',
        canonicalUrl:
            'https://scholarsphere.example/opportunities/research-scholarship',
        indexable: true,
      ),
    );
    await portal.publish(
      const PublicPageMetadata(
        path: '/applicant/profile',
        title: 'Private profile',
        description: 'Applicant profile',
        canonicalUrl: 'https://scholarsphere.example/applicant/profile',
        indexable: false,
      ),
    );
    final sitemap = await portal.sitemap();
    expect(sitemap, contains('research-scholarship'));
    expect(sitemap, isNot(contains('applicant/profile')));
  });
}
