import 'source_record.dart';

abstract class SourceRegistryRepository {
  Future<List<SourceRecord>> getAll();
  Future<SourceRecord> register(SourceRecord source);
  Future<SourceRecord> review({
    required String sourceId,
    required ReliabilityLevel trustLevel,
    required SourceVerificationStatus status,
  });
  Future<SourceRecord?> approvedSourceFor(String location);
  Future<SourceRecord> recordAccess(
    String sourceId, {
    required bool successful,
  });
  Future<SourceRecord> recordCorrection(String sourceId);
}

class SourceRegistryFailure implements Exception {
  const SourceRegistryFailure(this.message);
  final String message;
}
