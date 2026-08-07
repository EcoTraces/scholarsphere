import 'privacy_models.dart';

abstract interface class PrivacyRepository {
  Future<void> setMinorStatus(String userId, bool isMinor);

  Future<List<ConsentRecord>> getConsents(String userId);

  Future<void> grantConsent({
    required String userId,
    required ConsentType type,
    required String policyVersion,
  });

  Future<void> withdrawConsent(String userId, ConsentType type);

  Future<PrivacyRequest> submitRequest({
    required String userId,
    required PrivacyRequestType type,
    String notes = '',
  });

  Future<List<PrivacyRequest>> getRequests(String userId);

  Future<List<OrganizationAccessRecord>> getAccessHistory(String userId);

  Future<void> recordOrganizationAccess({
    required String userId,
    required String organizationId,
    required String organizationName,
    required Set<String> dataCategories,
  });

  Future<void> recordIncident(PrivacyIncident incident);

  Future<List<PrivacyIncident>> getIncidentsForAdministration();
}
