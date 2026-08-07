import '../../authentication/domain/user_account.dart';

enum Permission {
  viewOpportunities,
  manageOwnProfile,
  manageOwnDocuments,
  trackApplications,
  submitOpportunity,
  manageProviderOpportunities,
  verifyOpportunity,
  moderateContent,
  supportUsers,
  viewAdministration,
  manageUsers,
  manageSecurity,
  suspendAccounts,
  manageSecrets,
  exportReports,
}

abstract final class AccessControlPolicy {
  static final Map<UserRole, Set<Permission>> _permissions = {
    UserRole.applicant: {
      Permission.viewOpportunities,
      Permission.manageOwnProfile,
      Permission.manageOwnDocuments,
      Permission.trackApplications,
    },
    UserRole.opportunityProvider: {
      Permission.viewOpportunities,
      Permission.submitOpportunity,
      Permission.manageProviderOpportunities,
    },
    UserRole.verificationOfficer: {
      Permission.viewOpportunities,
      Permission.verifyOpportunity,
    },
    UserRole.moderator: {
      Permission.viewOpportunities,
      Permission.moderateContent,
    },
    UserRole.supportOfficer: {
      Permission.viewOpportunities,
      Permission.supportUsers,
    },
    UserRole.administrator: {
      Permission.viewOpportunities,
      Permission.viewAdministration,
      Permission.manageUsers,
      Permission.exportReports,
    },
    UserRole.securityAdministrator: {
      Permission.viewAdministration,
      Permission.manageSecurity,
      Permission.suspendAccounts,
      Permission.manageSecrets,
    },
    UserRole.superAdministrator: Permission.values.toSet(),
  };

  static bool allows(UserRole role, Permission permission) =>
      _permissions[role]?.contains(permission) ?? false;

  static bool requiresStrongAuthentication(UserRole role) => {
    UserRole.administrator,
    UserRole.securityAdministrator,
    UserRole.superAdministrator,
  }.contains(role);

  static bool requiresReauthentication(Permission permission) => {
    Permission.manageUsers,
    Permission.manageSecurity,
    Permission.suspendAccounts,
    Permission.manageSecrets,
    Permission.exportReports,
  }.contains(permission);
}
