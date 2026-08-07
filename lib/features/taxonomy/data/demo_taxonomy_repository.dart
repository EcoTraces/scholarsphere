import '../domain/taxonomy.dart';
import '../domain/taxonomy_repository.dart';

class DemoTaxonomyRepository implements TaxonomyRepository {
  DemoTaxonomyRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now {
    _seed();
  }

  final DateTime Function() _clock;
  final Map<String, TaxonomyTerm> _terms = {};
  final List<TaxonomyVersion> _versions = [];
  int _version = 1;

  @override
  Future<TaxonomyTerm> save(
    TaxonomyTerm term, {
    required String actorId,
    required String reason,
  }) async {
    final normalized = _normalize(term.canonicalName);
    final collision = _terms.values.where(
      (item) =>
          item.id != term.id &&
          item.type == term.type &&
          (_normalize(item.canonicalName) == normalized ||
              item.synonyms.map(_normalize).contains(normalized)),
    );
    if (collision.isNotEmpty) {
      throw StateError('A canonical or synonymous taxonomy term exists.');
    }
    _version++;
    final saved = term.copyWith(version: _version, updatedAt: _clock());
    _terms[saved.id] = saved;
    _recordVersion(actorId, reason);
    return saved;
  }

  @override
  Future<TaxonomyTerm?> resolve(TaxonomyType type, String value) async {
    final normalized = _normalize(value);
    for (final term in _terms.values) {
      if (term.active &&
          term.type == type &&
          (_normalize(term.canonicalName) == normalized ||
              term.synonyms.map(_normalize).contains(normalized) ||
              (term.code != null && _normalize(term.code!) == normalized))) {
        return term;
      }
    }
    return null;
  }

  @override
  Future<List<TaxonomyTerm>> list(
    TaxonomyType type, {
    bool activeOnly = true,
  }) async => _terms.values
      .where((item) => item.type == type && (!activeOnly || item.active))
      .toList();

  @override
  Future<List<List<TaxonomyTerm>>> duplicateCandidates(
    TaxonomyType type,
  ) async {
    final terms = await list(type, activeOnly: false);
    final groups = <List<TaxonomyTerm>>[];
    final used = <String>{};
    for (final term in terms) {
      if (used.contains(term.id)) continue;
      final tokens = {
        _normalize(term.canonicalName),
        ...term.synonyms.map(_normalize),
      };
      final matches = terms.where((other) {
        if (other.id == term.id) return true;
        final otherTokens = {
          _normalize(other.canonicalName),
          ...other.synonyms.map(_normalize),
        };
        return tokens.intersection(otherTokens).isNotEmpty;
      }).toList();
      if (matches.length > 1) {
        groups.add(matches);
        used.addAll(matches.map((item) => item.id));
      }
    }
    return groups;
  }

  @override
  Future<TaxonomyTerm> merge({
    required String canonicalId,
    required Set<String> duplicateIds,
    required String actorId,
  }) async {
    final canonical = _terms[canonicalId];
    if (canonical == null) throw StateError('Canonical term not found.');
    final duplicates = duplicateIds
        .map((id) => _terms[id])
        .whereType<TaxonomyTerm>()
        .where((item) => item.type == canonical.type)
        .toList();
    _version++;
    final merged = canonical.copyWith(
      synonyms: {
        ...canonical.synonyms,
        ...duplicates.map((item) => item.canonicalName),
        ...duplicates.expand((item) => item.synonyms),
      },
      version: _version,
      updatedAt: _clock(),
    );
    _terms[canonicalId] = merged;
    for (final duplicate in duplicates) {
      _terms[duplicate.id] = duplicate.copyWith(
        active: false,
        version: _version,
        updatedAt: _clock(),
      );
    }
    _recordVersion(actorId, 'Merged duplicate taxonomy terms.');
    return merged;
  }

  @override
  Future<List<TaxonomyVersion>> versions() async =>
      List.unmodifiable(_versions.reversed);

  String _normalize(String value) =>
      value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), ' ').trim();

  void _recordVersion(String actor, String reason) {
    _versions.add(
      TaxonomyVersion(
        version: _version,
        createdAt: _clock(),
        createdBy: actor,
        reason: reason,
        termCount: _terms.length,
      ),
    );
  }

  void _seed() {
    final now = _clock();
    _terms['field-computer-science'] = TaxonomyTerm(
      id: 'field-computer-science',
      type: TaxonomyType.academicField,
      canonicalName: 'Computer Science',
      code: 'CS',
      synonyms: const {
        'Computer Sciences',
        'Computing',
        'BSc Computer Science',
      },
      parentId: null,
      active: true,
      version: 1,
      createdAt: now,
      updatedAt: now,
    );
    _terms['country-canada'] = TaxonomyTerm(
      id: 'country-canada',
      type: TaxonomyType.country,
      canonicalName: 'Canada',
      code: 'CA',
      synonyms: const {},
      parentId: 'region-north-america',
      active: true,
      version: 1,
      createdAt: now,
      updatedAt: now,
    );
    _recordVersion('system', 'Initial taxonomy.');
  }
}
