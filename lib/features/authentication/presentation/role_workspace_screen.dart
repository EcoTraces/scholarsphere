import 'package:flutter/material.dart';

import '../domain/user_account.dart';

class RoleWorkspaceScreen extends StatelessWidget {
  const RoleWorkspaceScreen({
    super.key,
    required this.user,
    required this.onSignOut,
  });

  final UserAccount user;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) {
    final destination = switch (user.role) {
      UserRole.applicant => 'Applicant workspace',
      UserRole.opportunityProvider => 'Provider workspace',
      UserRole.verificationOfficer => 'Verification queue',
      UserRole.moderator => 'Moderation workspace',
      UserRole.supportOfficer => 'Support workspace',
      UserRole.administrator => 'Administration',
      UserRole.securityAdministrator => 'Security administration',
      UserRole.superAdministrator => 'System administration',
    };
    return Scaffold(
      appBar: AppBar(
        title: const Text('ScholarSphere'),
        actions: [
          IconButton(
            onPressed: onSignOut,
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 680),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.admin_panel_settings_outlined, size: 48),
                const SizedBox(height: 16),
                Text(
                  destination,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  'Signed in as ${user.fullName} (${user.roleLabel})',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                const Text(
                  'This account is authorized for its dedicated workspace. '
                  'The workflow will be implemented in its feature module.',
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
