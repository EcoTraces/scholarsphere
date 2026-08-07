enum RetentionAction { delete, anonymize, retainForLegalObligation }

class DataRetentionRule {
  const DataRetentionRule({
    required this.category,
    required this.duration,
    required this.action,
  });

  final String category;
  final Duration duration;
  final RetentionAction action;
}

abstract final class ScholarSphereRetentionPolicy {
  static const rules = [
    DataRetentionRule(
      category: 'inactive-account-profile',
      duration: Duration(days: 730),
      action: RetentionAction.anonymize,
    ),
    DataRetentionRule(
      category: 'uploaded-documents-after-account-deletion',
      duration: Duration(days: 30),
      action: RetentionAction.delete,
    ),
    DataRetentionRule(
      category: 'security-audit-log',
      duration: Duration(days: 365),
      action: RetentionAction.retainForLegalObligation,
    ),
    DataRetentionRule(
      category: 'withdrawn-marketing-consent',
      duration: Duration(days: 30),
      action: RetentionAction.delete,
    ),
  ];
}

abstract interface class DataProtectionGateway {
  Future<String> pseudonymize(String userId);

  Future<void> anonymizeUser(String userId);

  Future<void> applyRetentionRules(DateTime asOf);
}
