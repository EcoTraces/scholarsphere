import '../../opportunities/domain/opportunity.dart';
import '../domain/application_record.dart';
import '../domain/application_repository.dart';

class DemoApplicationRepository implements ApplicationRepository {
  DemoApplicationRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final Map<String, ApplicationRecord> _records = {};

  @override
  Future<List<ApplicationRecord>> getForUser(String userId) async {
    final records =
        _records.values.where((item) => item.userId == userId).toList()
          ..sort((left, right) => right.updatedAt.compareTo(left.updatedAt));
    return records;
  }

  @override
  Future<ApplicationRecord?> getForOpportunity(
    String userId,
    String opportunityId,
  ) async => _records['$userId-$opportunityId'];

  @override
  Future<ApplicationRecord> saveOpportunity(
    String userId,
    Opportunity opportunity,
  ) async {
    final id = '$userId-${opportunity.id}';
    final existing = _records[id];
    if (existing != null) return existing;
    final record = ApplicationRecord.saved(
      userId: userId,
      opportunity: opportunity,
      now: _clock(),
    );
    _records[id] = record;
    return record;
  }

  @override
  Future<void> update(ApplicationRecord record) async {
    if (!_records.containsKey(record.id)) {
      throw StateError('Application record not found.');
    }
    _records[record.id] = record.copyWith(updatedAt: _clock());
  }

  @override
  Future<List<ApplicationRecord>> getAllForAdministration() async =>
      _records.values.toList();
}
