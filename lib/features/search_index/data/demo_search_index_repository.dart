import '../../opportunities/domain/opportunity.dart';
import '../../search/domain/opportunity_search.dart';
import '../domain/search_index.dart';
import '../domain/search_index_repository.dart';

class DemoSearchIndexRepository implements SearchIndexRepository {
  DemoSearchIndexRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final Map<String, Opportunity> _index = {};
  final List<SearchHistoryEntry> _history = [];
  final Map<String, Set<String>> _synonyms = {
    'scholarship': {'funding', 'award', 'grant'},
    'masters': {'master', 'graduate', 'postgraduate'},
    'phd': {'doctorate', 'doctoral'},
    'online': {'remote', 'virtual'},
  };
  final OpportunitySearch _filters = const OpportunitySearch();

  @override
  Future<void> synchronize(Iterable<Opportunity> opportunities) async {
    final incoming = {for (final item in opportunities) item.id: item};
    _index.removeWhere((id, _) => !incoming.containsKey(id));
    for (final item in incoming.values) {
      await upsert(item);
    }
  }

  @override
  Future<void> upsert(Opportunity opportunity) async {
    if ({
      VerificationStatus.archived,
      VerificationStatus.rejected,
      VerificationStatus.expired,
    }.contains(opportunity.verificationStatus)) {
      _index.remove(opportunity.id);
      return;
    }
    _index[opportunity.id] = opportunity;
  }

  @override
  Future<void> remove(String opportunityId) async {
    _index.remove(opportunityId);
  }

  @override
  Future<int> rebuild(Iterable<Opportunity> opportunities) async {
    _index.clear();
    await synchronize(opportunities);
    return _index.length;
  }

  @override
  Future<DiscoverySearchResult> search(DiscoverySearchRequest request) async {
    if (request.page < 1 || request.pageSize < 1 || request.pageSize > 100) {
      throw ArgumentError('Invalid search pagination.');
    }
    final now = _clock();
    final filter = request.filter.copyWith(query: '');
    final candidates = _filters.apply(_index.values, filter, now: now);
    final terms = _expand(_tokenize(request.query));
    final hits = <SearchHit>[];
    for (final opportunity in candidates) {
      final score = _score(
        opportunity,
        terms,
        request.eligibilityScores[opportunity.id] ?? 0,
        request.sourceTrustScores[opportunity.id] ?? 0,
        now,
      );
      if (terms.isEmpty || score.$1 > 0) {
        hits.add(
          SearchHit(
            opportunity: opportunity,
            score: score.$1,
            matchedTerms: score.$2,
          ),
        );
      }
    }
    hits.sort((a, b) => b.score.compareTo(a.score));
    final total = hits.length;
    final start = (request.page - 1) * request.pageSize;
    final paged = start >= total
        ? <SearchHit>[]
        : hits.sublist(
            start,
            (start + request.pageSize).clamp(0, total).toInt(),
          );
    if (request.userId != null && request.query.trim().isNotEmpty) {
      _history.add(
        SearchHistoryEntry(
          userId: request.userId!,
          query: request.query.trim(),
          resultCount: total,
          searchedAt: now,
        ),
      );
    }
    return DiscoverySearchResult(
      hits: paged,
      total: total,
      facets: _facets(hits.map((hit) => hit.opportunity)),
      suggestions: total == 0
          ? await _noResultSuggestions(request.query)
          : const [],
      page: request.page,
      pageSize: request.pageSize,
    );
  }

  @override
  Future<List<String>> autocomplete(String prefix, {int limit = 8}) async {
    final normalized = prefix.trim().toLowerCase();
    if (normalized.isEmpty) return const [];
    final candidates = <String>{
      for (final item in _index.values) ...[
        item.title,
        item.provider,
        item.hostInstitution,
        item.hostCountry,
        ...item.fieldsOfStudy,
      ],
    };
    final ranked =
        candidates
            .where((value) => value.toLowerCase().contains(normalized))
            .toList()
          ..sort((a, b) {
            final aStarts = a.toLowerCase().startsWith(normalized);
            final bStarts = b.toLowerCase().startsWith(normalized);
            return aStarts == bStarts ? a.compareTo(b) : (aStarts ? -1 : 1);
          });
    return ranked.take(limit).toList();
  }

  @override
  Future<List<SearchHistoryEntry>> history(String userId) async => _history
      .where((entry) => entry.userId == userId)
      .toList()
      .reversed
      .toList();

  @override
  Future<void> clearHistory(String userId) async {
    _history.removeWhere((entry) => entry.userId == userId);
  }

  @override
  Future<List<PopularSearch>> popularSearches({int limit = 10}) async {
    final counts = <String, int>{};
    for (final entry in _history) {
      final query = entry.query.toLowerCase();
      counts.update(query, (count) => count + 1, ifAbsent: () => 1);
    }
    final popular =
        counts.entries
            .map((entry) => PopularSearch(query: entry.key, count: entry.value))
            .toList()
          ..sort((a, b) => b.count.compareTo(a.count));
    return popular.take(limit).toList();
  }

  (double, List<String>) _score(
    Opportunity item,
    Set<String> terms,
    int eligibility,
    int sourceTrust,
    DateTime now,
  ) {
    final fields = <(String, double)>[
      (item.title, 12),
      (item.provider, 8),
      (item.hostInstitution, 7),
      (item.hostCountry, 5),
      (item.fieldsOfStudy.join(' '), 6),
      (item.summary, 3),
      (item.eligibilityRequirements.join(' '), 2),
    ];
    var relevance = 0.0;
    final matched = <String>{};
    for (final term in terms) {
      for (final field in fields) {
        final tokens = _tokenize(field.$1);
        if (tokens.any(
          (token) =>
              token == term || _distance(token, term) <= _tolerance(term),
        )) {
          relevance += field.$2;
          matched.add(term);
        }
      }
    }
    if (terms.isNotEmpty && matched.isEmpty) return (0, const []);
    var ranking = relevance;
    if (item.isVerified) ranking += 30;
    if (item.deadline.isAfter(now)) ranking += 18;
    ranking += eligibility * .2;
    ranking += sourceTrust * .12;
    if (item.lastVerifiedAt != null) {
      final age = now.difference(item.lastVerifiedAt!).inDays;
      ranking += (15 - age / 30).clamp(0, 15).toDouble();
    }
    final daysToDeadline = item.deadline.difference(now).inDays;
    if (daysToDeadline >= 7 && daysToDeadline <= 90) ranking += 8;
    return (ranking, matched.toList());
  }

  Set<String> _expand(Set<String> terms) {
    final expanded = {...terms};
    for (final term in terms) {
      for (final entry in _synonyms.entries) {
        if (term == entry.key || entry.value.contains(term)) {
          expanded.add(entry.key);
          expanded.addAll(entry.value);
        }
      }
    }
    return expanded;
  }

  Set<String> _tokenize(String value) => RegExp(
    r'[a-z0-9]+',
  ).allMatches(value.toLowerCase()).map((match) => match.group(0)!).toSet();

  int _tolerance(String term) => term.length >= 7
      ? 2
      : term.length >= 4
      ? 1
      : 0;

  int _distance(String left, String right) {
    final previous = List<int>.generate(right.length + 1, (index) => index);
    for (var i = 0; i < left.length; i++) {
      var diagonal = previous[0];
      previous[0] = i + 1;
      for (var j = 0; j < right.length; j++) {
        final old = previous[j + 1];
        previous[j + 1] = left[i] == right[j]
            ? diagonal
            : 1 + [diagonal, previous[j], old].reduce((a, b) => a < b ? a : b);
        diagonal = old;
      }
    }
    return previous.last;
  }

  SearchFacets _facets(Iterable<Opportunity> opportunities) {
    final countries = <String, int>{};
    final funding = <String, int>{};
    final levels = <String, int>{};
    final institutions = <String, int>{};
    for (final item in opportunities) {
      _increment(countries, item.hostCountry);
      _increment(funding, item.fundingLabel);
      _increment(institutions, item.hostInstitution);
      for (final level in item.studyLevels) {
        _increment(levels, level);
      }
    }
    return SearchFacets(
      countries: countries,
      funding: funding,
      studyLevels: levels,
      institutions: institutions,
    );
  }

  void _increment(Map<String, int> values, String key) {
    values.update(key, (count) => count + 1, ifAbsent: () => 1);
  }

  Future<List<String>> _noResultSuggestions(String query) async {
    final terms = _tokenize(query);
    final candidates = <String>{
      for (final item in _index.values) ...item.fieldsOfStudy,
      for (final item in _index.values) item.hostCountry,
    };
    final ranked = candidates.toList()
      ..sort((a, b) {
        final aDistance = terms.isEmpty
            ? 0
            : terms
                  .map((term) => _distance(a.toLowerCase(), term))
                  .reduce((x, y) => x < y ? x : y);
        final bDistance = terms.isEmpty
            ? 0
            : terms
                  .map((term) => _distance(b.toLowerCase(), term))
                  .reduce((x, y) => x < y ? x : y);
        return aDistance.compareTo(bDistance);
      });
    return ranked.take(5).toList();
  }
}
