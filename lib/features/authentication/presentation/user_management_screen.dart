import 'package:flutter/material.dart';

import '../domain/auth_repository.dart';
import '../domain/user_account.dart';

class UserManagementScreen extends StatefulWidget {
  const UserManagementScreen({
    super.key,
    required this.repository,
    required this.administrator,
  });

  final AuthRepository repository;
  final UserAccount administrator;

  @override
  State<UserManagementScreen> createState() => _UserManagementScreenState();
}

class _UserManagementScreenState extends State<UserManagementScreen> {
  late Future<List<UserAccount>> _accounts;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _accounts = widget.repository.getAllForAdministration();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Users and access'),
      actions: [
        IconButton(
          tooltip: 'Create account',
          onPressed: _createAccount,
          icon: const Icon(Icons.person_add_alt_1_outlined),
        ),
      ],
    ),
    floatingActionButton: FloatingActionButton.extended(
      onPressed: _createAccount,
      icon: const Icon(Icons.person_add_alt_1_outlined),
      label: const Text('Create account'),
    ),
    body: FutureBuilder<List<UserAccount>>(
      future: _accounts,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final accounts = snapshot.data!;
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
          itemCount: accounts.length,
          separatorBuilder: (_, _) => const Divider(height: 1),
          itemBuilder: (context, index) {
            final account = accounts[index];
            return ListTile(
              leading: CircleAvatar(child: Text(account.fullName[0])),
              title: Text(account.fullName),
              subtitle: Text('${account.email} | ${account.roleLabel}'),
              trailing: Chip(label: Text(account.status.name)),
            );
          },
        );
      },
    ),
  );

  Future<void> _createAccount() async {
    final created = await showDialog<bool>(
      context: context,
      builder: (_) => _CreateManagedAccountDialog(
        repository: widget.repository,
        administrator: widget.administrator,
      ),
    );
    if (created == true && mounted) setState(_reload);
  }
}

class _CreateManagedAccountDialog extends StatefulWidget {
  const _CreateManagedAccountDialog({
    required this.repository,
    required this.administrator,
  });

  final AuthRepository repository;
  final UserAccount administrator;

  @override
  State<_CreateManagedAccountDialog> createState() =>
      _CreateManagedAccountDialogState();
}

class _CreateManagedAccountDialogState
    extends State<_CreateManagedAccountDialog> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  UserRole _role = UserRole.opportunityProvider;
  bool _busy = false;
  bool _obscurePassword = true;
  String? _error;

  static const _standardManagedRoles = [
    UserRole.opportunityProvider,
    UserRole.verificationOfficer,
    UserRole.moderator,
    UserRole.supportOfficer,
  ];

  static const _privilegedManagedRoles = [
    UserRole.administrator,
    UserRole.securityAdministrator,
    UserRole.superAdministrator,
  ];

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Create actor account'),
    content: SizedBox(
      width: 480,
      child: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _name,
                decoration: const InputDecoration(labelText: 'Full name'),
                validator: (value) => (value?.trim().length ?? 0) < 2
                    ? "Enter the actor's full name."
                    : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'Email address'),
                validator: (value) => (value?.contains('@') ?? false)
                    ? null
                    : 'Enter a valid email address.',
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<UserRole>(
                initialValue: _role,
                decoration: const InputDecoration(labelText: 'Role'),
                items: [
                  for (final role in [
                    ..._standardManagedRoles,
                    if (widget.administrator.role ==
                        UserRole.superAdministrator)
                      ..._privilegedManagedRoles,
                  ])
                    DropdownMenuItem(value: role, child: Text(_label(role))),
                ],
                onChanged: _busy
                    ? null
                    : (value) => setState(() => _role = value ?? _role),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _password,
                obscureText: _obscurePassword,
                decoration: InputDecoration(
                  labelText: 'Temporary password',
                  suffixIcon: IconButton(
                    tooltip: _obscurePassword
                        ? 'Show password'
                        : 'Hide password',
                    onPressed: () =>
                        setState(() => _obscurePassword = !_obscurePassword),
                    icon: Icon(
                      _obscurePassword
                          ? Icons.visibility_outlined
                          : Icons.visibility_off_outlined,
                    ),
                  ),
                ),
                validator: (value) => (value?.length ?? 0) < 12
                    ? 'Use at least 12 characters.'
                    : null,
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
            ],
          ),
        ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: _busy ? null : () => Navigator.pop(context, false),
        child: const Text('Cancel'),
      ),
      FilledButton(
        onPressed: _busy ? null : _submit,
        child: Text(_busy ? 'Creating...' : 'Create account'),
      ),
    ],
  );

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.repository.createManagedAccount(
        fullName: _name.text,
        email: _email.text,
        temporaryPassword: _password.text,
        role: _role,
      );
      if (mounted) Navigator.pop(context, true);
    } on AuthFailure catch (failure) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = failure.message;
        });
      }
    }
  }

  static String _label(UserRole role) => switch (role) {
    UserRole.opportunityProvider => 'Opportunity provider',
    UserRole.verificationOfficer => 'Verification officer',
    UserRole.moderator => 'Moderator',
    UserRole.supportOfficer => 'Support officer',
    UserRole.administrator => 'Administrator',
    UserRole.securityAdministrator => 'Security administrator',
    UserRole.superAdministrator => 'Super administrator',
    UserRole.applicant => 'Applicant',
  };
}
