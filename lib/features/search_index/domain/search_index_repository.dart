import '../../opportunities/domain/opportunity.dart';
import 'search_index.dart';

abstract class SearchIndexRepository {
  Future<void> synchronize(Iterable<Opportunity> opportunities);
  Future<void> upsert(Opportunity opportunity);
  Future<void> remove(String opportunityId);
  Future<int> rebuild(Iterable<Opportunity> opportunities);
  Future<DiscoverySearchResult> search(DiscoverySearchRequest request);
  Future<List<String>> autocomplete(String prefix, {int limit = 8});
  Future<List<SearchHistoryEntry>> history(String userId);
  Future<void> clearHistory(String userId);
  Future<List<PopularSearch>> popularSearches({int limit = 10});
}
