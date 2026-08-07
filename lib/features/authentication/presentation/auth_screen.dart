import 'package:flutter/material.dart';

import '../domain/auth_repository.dart';
import '../domain/user_account.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({
    super.key,
    required this.repository,
    required this.onAuthenticated,
  });

  final AuthRepository repository;
  final ValueChanged<UserAccount> onAuthenticated;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _registering = false;
  bool _obscurePassword = true;
  bool _busy = false;
  bool _acceptPrivacy = false;
  bool _acceptTerms = false;
  String? _error;

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.public, size: 42),
                  const SizedBox(height: 12),
                  Text(
                    'ScholarSphere',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _registering
                        ? 'Create your account'
                        : 'Sign in to discover trusted opportunities',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 28),
                  SegmentedButton<bool>(
                    segments: const [
                      ButtonSegment(value: false, label: Text('Sign in')),
                      ButtonSegment(value: true, label: Text('Register')),
                    ],
                    selected: {_registering},
                    onSelectionChanged: _busy
                        ? null
                        : (value) => setState(() {
                            _registering = value.first;
                            _error = null;
                          }),
                  ),
                  const SizedBox(height: 24),
                  Form(
                    key: _formKey,
                    child: Column(
                      children: [
                        if (_registering) ...[
                          TextFormField(
                            controller: _nameController,
                            textInputAction: TextInputAction.next,
                            decoration: const InputDecoration(
                              labelText: 'Full name',
                              prefixIcon: Icon(Icons.person_outline),
                            ),
                            validator: (value) =>
                                value == null || value.trim().length < 2
                                ? 'Enter your full name.'
                                : null,
                          ),
                          const SizedBox(height: 14),
                        ],
                        TextFormField(
                          key: const Key('auth-email'),
                          controller: _emailController,
                          keyboardType: TextInputType.emailAddress,
                          textInputAction: TextInputAction.next,
                          decoration: const InputDecoration(
                            labelText: 'Email address',
                            prefixIcon: Icon(Icons.mail_outline),
                          ),
                          validator: (value) {
                            final email = value?.trim() ?? '';
                            return email.contains('@')
                                ? null
                                : 'Enter a valid email address.';
                          },
                        ),
                        const SizedBox(height: 14),
                        TextFormField(
                          key: const Key('auth-password'),
                          controller: _passwordController,
                          obscureText: _obscurePassword,
                          onFieldSubmitted: (_) => _submit(),
                          decoration: InputDecoration(
                            labelText: 'Password',
                            prefixIcon: const Icon(Icons.lock_outline),
                            suffixIcon: IconButton(
                              tooltip: _obscurePassword
                                  ? 'Show password'
                                  : 'Hide password',
                              onPressed: () => setState(
                                () => _obscurePassword = !_obscurePassword,
                              ),
                              icon: Icon(
                                _obscurePassword
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                              ),
                            ),
                          ),
                          validator: (value) {
                            final password = value ?? '';
                            if (!_registering) {
                              return password.isEmpty
                                  ? 'Enter your password.'
                                  : null;
                            }
                            if (password.length < 12) {
                              return 'Use at least 12 characters.';
                            }
                            if (!RegExp('[A-Z]').hasMatch(password) ||
                                !RegExp('[a-z]').hasMatch(password) ||
                                !RegExp('[0-9]').hasMatch(password) ||
                                !RegExp(r'[^A-Za-z0-9]').hasMatch(password)) {
                              return 'Use upper/lowercase, a number, and a symbol.';
                            }
                            return null;
                          },
                        ),
                        if (_registering) ...[
                          const SizedBox(height: 14),
                          CheckboxListTile(
                            contentPadding: EdgeInsets.zero,
                            value: _acceptPrivacy,
                            title: const Text('Accept the privacy policy'),
                            onChanged: _busy
                                ? null
                                : (value) => setState(
                                    () => _acceptPrivacy = value ?? false,
                                  ),
                          ),
                          CheckboxListTile(
                            contentPadding: EdgeInsets.zero,
                            value: _acceptTerms,
                            title: const Text(
                              'Accept the terms and conditions',
                            ),
                            onChanged: _busy
                                ? null
                                : (value) => setState(
                                    () => _acceptTerms = value ?? false,
                                  ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 14),
                    Text(
                      _error!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                  if (!_registering)
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: _busy ? null : _resetPassword,
                        child: const Text('Forgot password?'),
                      ),
                    )
                  else
                    const SizedBox(height: 18),
                  FilledButton(
                    key: const Key('auth-submit'),
                    onPressed: _busy ? null : _submit,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      child: _busy
                          ? const SizedBox.square(
                              dimension: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Text(_registering ? 'Create account' : 'Sign in'),
                    ),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _signInWithGoogle,
                    icon: const Icon(Icons.login),
                    label: const Text('Continue with Google'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_registering && (!_acceptPrivacy || !_acceptTerms)) {
      setState(
        () => _error =
            'Accept the privacy policy and terms to create an account.',
      );
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final account = _registering
          ? await widget.repository.register(
              fullName: _nameController.text,
              email: _emailController.text,
              password: _passwordController.text,
              role: UserRole.applicant,
            )
          : await widget.repository.signIn(
              email: _emailController.text,
              password: _passwordController.text,
            );
      if (!mounted) return;
      if (!account.emailVerified) {
        await _showVerificationDialog();
      } else {
        widget.onAuthenticated(account);
      }
    } on AuthFailure catch (failure) {
      if (mounted) setState(() => _error = failure.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _showVerificationDialog() async {
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Verify your email'),
        content: Text(
          'Open the verification link sent to '
          '${_emailController.text.trim()}, then check again.',
        ),
        actions: [
          TextButton(
            onPressed: () async {
              try {
                await widget.repository.sendEmailVerification();
                if (!dialogContext.mounted) return;
                ScaffoldMessenger.of(dialogContext).showSnackBar(
                  const SnackBar(content: Text('Verification email sent.')),
                );
              } on AuthFailure catch (failure) {
                if (!dialogContext.mounted) return;
                ScaffoldMessenger.of(dialogContext).showSnackBar(
                  SnackBar(content: Text(failure.message)),
                );
              }
            },
            child: const Text('Resend email'),
          ),
          FilledButton(
            onPressed: () async {
              try {
                final account = await widget.repository
                    .confirmEmailVerification();
                if (!dialogContext.mounted) return;
                Navigator.of(dialogContext).pop();
                widget.onAuthenticated(account);
              } on AuthFailure catch (failure) {
                if (!dialogContext.mounted) return;
                ScaffoldMessenger.of(dialogContext).showSnackBar(
                  SnackBar(content: Text(failure.message)),
                );
              }
            },
            child: const Text('Check verification'),
          ),
        ],
      ),
    );
  }

  Future<void> _signInWithGoogle() async {
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Privacy and terms'),
        content: const Text(
          'Continuing with Google creates an account and records your '
          'acceptance of the ScholarSphere privacy policy and terms.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Accept and continue'),
          ),
        ],
      ),
    );
    if (accepted != true || !mounted) return;
    setState(() => _busy = true);
    final account = await widget.repository.signInWithGoogle();
    if (!mounted) return;
    setState(() => _busy = false);
    widget.onAuthenticated(account);
  }

  Future<void> _resetPassword() async {
    final email = _emailController.text.trim();
    if (!email.contains('@')) {
      setState(() => _error = 'Enter your email address first.');
      return;
    }
    await widget.repository.sendPasswordReset(email);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'If an account exists, password reset instructions were sent.',
        ),
      ),
    );
  }
}
