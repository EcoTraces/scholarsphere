import 'taxonomy.dart';

abstract class TaxonomyRepository {
  Future<TaxonomyTerm> save(
    TaxonomyTerm term, {
    required String actorId,
    required String reason,
  });
  Future<TaxonomyTerm?> resolve(TaxonomyType type, String value);
  Future<List<TaxonomyTerm>> list(TaxonomyType type, {bool activeOnly = true});
  Future<List<List<TaxonomyTerm>>> duplicateCandidates(TaxonomyType type);
  Future<TaxonomyTerm> merge({
    required String canonicalId,
    required Set<String> duplicateIds,
    required String actorId,
  });
  Future<List<TaxonomyVersion>> versions();
}
