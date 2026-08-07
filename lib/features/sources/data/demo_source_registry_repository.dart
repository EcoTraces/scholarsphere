import '../domain/source_record.dart';
import '../domain/source_registry_repository.dart';

class DemoSourceRegistryRepository implements SourceRegistryRepository {
  DemoSourceRegistryRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final Map<String, SourceRecord> _sources = {};

  @override
  Future<List<SourceRecord>> getAll() async =>
      _sources.values.toList()..sort((a, b) => a.name.compareTo(b.name));

  @override
  Future<SourceRecord> register(SourceRecord source) async {
    final domain = _normalizeDomain(source.domain);
    if (domain.isEmpty) {
      throw const SourceRegistryFailure('A valid source domain is required.');
    }
    if (_sources.values.any(
      (item) => _normalizeDomain(item.domain) == domain,
    )) {
      throw const SourceRegistryFailure(
        'This source domain is already registered.',
      );
    }
    final saved = source.copyWith(
      verificationStatus: SourceVerificationStatus.pending,
      trustScore: _score(source),
      updatedAt: _clock(),
    );
    _sources[saved.id] = saved;
    return saved;
  }

  @override
  Future<SourceRecord> review({
    required String sourceId,
    required ReliabilityLevel trustLevel,
    required SourceVerificationStatus status,
  }) async {
    final current = _require(sourceId);
    final updated = current.copyWith(
      trustLevel: trustLevel,
      verificationStatus: status,
      isBlocked: status == SourceVerificationStatus.blocked,
      trustScore: _score(current.copyWith(trustLevel: trustLevel)),
      updatedAt: _clock(),
    );
    _sources[sourceId] = updated;
    return updated;
  }

  @override
  Future<SourceRecord?> approvedSourceFor(String location) async {
    final host = _normalizeDomain(location);
    for (final source in _sources.values) {
      final domain = _normalizeDomain(source.domain);
      if (source.isApproved && (host == domain || host.endsWith('.$domain')))
        return source;
    }
    return null;
  }

  @override
  Future<SourceRecord> recordAccess(
    String sourceId, {
    required bool successful,
  }) async {
    final current = _require(sourceId);
    final now = _clock();
    final updated = current.copyWith(
      lastCheckedAt: now,
      lastSuccessfulAccess: successful ? now : current.lastSuccessfulAccess,
      rejectionCount: successful
          ? current.rejectionCount
          : current.rejectionCount + 1,
      trustScore: _score(current),
      updatedAt: now,
    );
    _sources[sourceId] = updated;
    return updated;
  }

  @override
  Future<SourceRecord> recordCorrection(String sourceId) async {
    final current = _require(sourceId);
    final updated = current.copyWith(
      correctionCount: current.correctionCount + 1,
      trustScore: _score(current) - 3,
      updatedAt: _clock(),
    );
    _sources[sourceId] = updated;
    return updated;
  }

  SourceRecord _require(String id) {
    final value = _sources[id];
    if (value == null)
      throw const SourceRegistryFailure('Source was not found.');
    return value;
  }

  String _normalizeDomain(String value) {
    final uri = Uri.tryParse(value.contains('://') ? value : 'https://$value');
    return (uri?.host ?? '').toLowerCase().replaceFirst(RegExp(r'^www\.'), '');
  }

  int _score(SourceRecord source) {
    final base = {
      ReliabilityLevel.a: 95,
      ReliabilityLevel.b: 85,
      ReliabilityLevel.c: 75,
      ReliabilityLevel.d: 62,
      ReliabilityLevel.e: 42,
      ReliabilityLevel.f: 10,
    }[source.trustLevel]!;
    return (base -
            source.correctionCount * 3 -
            source.rejectionCount * 5 +
            ((source.accuracyRate - .8) * 20).round())
        .clamp(0, 100)
        .toInt();
  }
}
