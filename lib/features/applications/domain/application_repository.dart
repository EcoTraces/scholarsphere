import '../../opportunities/domain/opportunity.dart';
import 'application_record.dart';

abstract interface class ApplicationRepository {
  Future<List<ApplicationRecord>> getForUser(String userId);

  Future<ApplicationRecord?> getForOpportunity(
    String userId,
    String opportunityId,
  );

  Future<ApplicationRecord> saveOpportunity(
    String userId,
    Opportunity opportunity,
  );

  Future<void> update(ApplicationRecord record);

  Future<List<ApplicationRecord>> getAllForAdministration();
}
