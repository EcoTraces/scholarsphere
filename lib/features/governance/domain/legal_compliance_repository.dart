import 'legal_compliance.dart';

abstract class LegalComplianceRepository {
  Future<LegalPolicy> publish(LegalPolicy policy);
  Future<LegalPolicy?> current(LegalPolicyType type);
  Future<List<LegalPolicy>> versions(LegalPolicyType type);
  Future<void> accept(PolicyAcceptance acceptance);
  Future<bool> hasAcceptedCurrent(String userId, LegalPolicyType type);
  Future<List<String>> pendingPolicyNotifications(String userId);
  Future<LegalRequest> submitLegalRequest(LegalRequest request);
  Future<List<LegalRequest>> legalRequests();
  Future<void> saveComplianceRecord(ComplianceRecord record);
  Future<List<ComplianceRecord>> complianceRecords();
}
