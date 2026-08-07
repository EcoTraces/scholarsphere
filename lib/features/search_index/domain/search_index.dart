import '../../opportunities/domain/opportunity.dart';
import '../../search/domain/opportunity_filter.dart';

class DiscoverySearchRequest {
  const DiscoverySearchRequest({
    required this.query,
    this.filter = const OpportunityFilter(),
    this.userId,
    this.page = 1,
    this.pageSize = 20,
    this.eligibilityScores = const {},
    this.sourceTrustScores = const {},
  });
  final String query;
  final OpportunityFilter filter;
  final String? userId;
  final int page;
  final int pageSize;
  final Map<String, int> eligibilityScores;
  final Map<String, int> sourceTrustScores;
}

class SearchHit {
  const SearchHit({
    required this.opportunity,
    required this.score,
    required this.matchedTerms,
  });
  final Opportunity opportunity;
  final double score;
  final List<String> matchedTerms;
}

class SearchFacets {
  const SearchFacets({
    required this.countries,
    required this.funding,
    required this.studyLevels,
    required this.institutions,
  });
  final Map<String, int> countries;
  final Map<String, int> funding;
  final Map<String, int> studyLevels;
  final Map<String, int> institutions;
}

class DiscoverySearchResult {
  const DiscoverySearchResult({
    required this.hits,
    required this.total,
    required this.facets,
    required this.suggestions,
    required this.page,
    required this.pageSize,
  });
  final List<SearchHit> hits;
  final int total;
  final SearchFacets facets;
  final List<String> suggestions;
  final int page;
  final int pageSize;
}

class SearchHistoryEntry {
  const SearchHistoryEntry({
    required this.userId,
    required this.query,
    required this.resultCount,
    required this.searchedAt,
  });
  final String userId;
  final String query;
  final int resultCount;
  final DateTime searchedAt;
}

class PopularSearch {
  const PopularSearch({required this.query, required this.count});
  final String query;
  final int count;
}
