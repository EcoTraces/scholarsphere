import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/background_jobs/data/demo_job_queue_repository.dart';
import 'package:scholarsphere/features/background_jobs/domain/background_job.dart';
import 'package:scholarsphere/features/experience/data/demo_experience_repository.dart';
import 'package:scholarsphere/features/experience/domain/experience_preferences.dart';
import 'package:scholarsphere/features/experience/domain/localized_formatter.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/opportunities/domain/opportunity.dart';
import 'package:scholarsphere/features/search/domain/opportunity_filter.dart';
import 'package:scholarsphere/features/search_index/data/demo_search_index_repository.dart';
import 'package:scholarsphere/features/search_index/domain/search_index.dart';

void main() {
  test(
    'job queue prioritizes work and dead-letters exhausted failures',
    () async {
      var now = DateTime.utc(2026, 7, 29);
      final repository = DemoJobQueueRepository(clock: () => now);
      final processed = <String>[];
      repository.registerHandler(
        BackgroundJobType.searchIndexUpdate,
        (job) async => processed.add(job.id),
      );
      repository.registerHandler(
        BackgroundJobType.documentScanning,
        (_) async => throw StateError('Scanner unavailable'),
      );
      final low = await repository.enqueue(
        type: BackgroundJobType.searchIndexUpdate,
        payload: const {},
        priority: JobPriority.low,
      );
      final high = await repository.enqueue(
        type: BackgroundJobType.searchIndexUpdate,
        payload: const {},
        priority: JobPriority.critical,
      );
      final failed = await repository.enqueue(
        type: BackgroundJobType.documentScanning,
        payload: const {},
        maxAttempts: 2,
      );

      expect((await repository.processNext('worker-1'))?.id, high.id);
      expect((await repository.processNext('worker-1'))?.id, failed.id);
      now = now.add(const Duration(seconds: 2));
      expect(
        (await repository.processNext('worker-1'))?.status,
        JobStatus.deadLettered,
      );
      expect((await repository.getDeadLetters()).single.id, failed.id);
      expect(await repository.getHistory(failed.id), hasLength(2));
      expect((await repository.processNext('worker-1'))?.id, low.id);
      expect((await repository.workerHealth()).single.healthy, isTrue);
    },
  );

  test(
    'search index supports typo tolerance, facets, history, and exclusion',
    () async {
      final opportunities = await DemoOpportunityRepository()
          .getAllForAdministration();
      final repository = DemoSearchIndexRepository(
        clock: () => DateTime(2026, 7, 29),
      );
      await repository.rebuild(opportunities);
      final result = await repository.search(
        const DiscoverySearchRequest(
          query: 'climte',
          userId: 'user',
          filter: OpportunityFilter(
            verifiedOnly: true,
            availability: OpportunityAvailability.open,
          ),
        ),
      );

      expect(result.hits.first.opportunity.title, contains('Climate'));
      expect(result.facets.countries, isNotEmpty);
      expect(await repository.history('user'), hasLength(1));
      expect((await repository.popularSearches()).first.query, 'climte');
      expect(await repository.autocomplete('glob'), isNotEmpty);

      final archived = result.hits.first.opportunity.copyWith(
        verificationStatus: VerificationStatus.archived,
      );
      await repository.upsert(archived);
      final afterArchive = await repository.search(
        const DiscoverySearchRequest(
          query: 'climate',
          filter: OpportunityFilter(
            verifiedOnly: false,
            availability: OpportunityAvailability.any,
          ),
        ),
      );
      expect(
        afterArchive.hits.any((hit) => hit.opportunity.id == archived.id),
        isFalse,
      );
    },
  );

  test(
    'experience preferences support RTL, formatting, translations, and cache',
    () async {
      final repository = DemoExperienceRepository();
      const preferences = ExperiencePreferences(
        language: SupportedLanguage.arabic,
        timezone: 'UTC+3',
        currencyCode: 'GHS',
        countryCode: 'GH',
        textScale: 1.5,
        highContrast: true,
        lowBandwidthMode: true,
        dataSaving: true,
      );
      await repository.savePreferences('user', preferences);
      await repository.saveTranslation(
        TranslationEntry(
          key: 'discover.title',
          language: SupportedLanguage.french,
          value: 'Decouvrir',
          updatedAt: DateTime(2026, 7, 29),
          updatedBy: 'translator',
        ),
      );
      await repository.cacheOpportunity('user', 'opportunity-1');

      final saved = await repository.getPreferences('user');
      expect(saved.language.isRightToLeft, isTrue);
      expect(
        LocalizedFormatter.date(DateTime(2026, 7, 29), saved),
        '29/07/2026',
      );
      expect(LocalizedFormatter.currency(25, saved), 'GHS 25.00');
      expect(
        await repository.translate('discover.title', SupportedLanguage.french),
        'Decouvrir',
      );
      expect(await repository.cachedOpportunities('user'), {'opportunity-1'});
    },
  );
}
