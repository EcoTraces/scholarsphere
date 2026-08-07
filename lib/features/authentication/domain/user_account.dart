enum UserRole {
  applicant,
  opportunityProvider,
  verificationOfficer,
  moderator,
  supportOfficer,
  administrator,
  securityAdministrator,
  superAdministrator,
}

enum AccountStatus { pendingVerification, active, suspended, deactivated }

class UserAccount {
  const UserAccount({
    required this.id,
    required this.fullName,
    required this.email,
    required this.role,
    required this.status,
    required this.emailVerified,
    this.twoFactorEnabled = false,
    this.marketingEmailsEnabled = false,
    this.deadlineNotificationsEnabled = true,
  });

  final String id;
  final String fullName;
  final String email;
  final UserRole role;
  final AccountStatus status;
  final bool emailVerified;
  final bool twoFactorEnabled;
  final bool marketingEmailsEnabled;
  final bool deadlineNotificationsEnabled;

  bool get canSignIn => status == AccountStatus.active;

  String get roleLabel => switch (role) {
    UserRole.applicant => 'Applicant',
    UserRole.opportunityProvider => 'Opportunity provider',
    UserRole.verificationOfficer => 'Verification officer',
    UserRole.moderator => 'Moderator',
    UserRole.supportOfficer => 'Support officer',
    UserRole.administrator => 'Administrator',
    UserRole.securityAdministrator => 'Security administrator',
    UserRole.superAdministrator => 'Super administrator',
  };
}
