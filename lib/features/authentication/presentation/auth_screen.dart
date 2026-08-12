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
  static const _wideBreakpoint = 900.0;

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

  void _setMode(bool registering) {
    if (_busy) return;
    setState(() {
      _registering = registering;
      _error = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final wide = constraints.maxWidth >= _wideBreakpoint;
            if (!wide) return _buildFormPane(theme, wide: false);
            return Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(flex: 6, child: _buildFormPane(theme, wide: true)),
                Expanded(flex: 5, child: _buildSidePanel(theme)),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildFormPane(ThemeData theme, {required bool wide}) {
    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildBrandRow(theme, centered: !wide),
        SizedBox(height: wide ? 40 : 28),
        Text(
          _registering ? 'Create your account' : 'Welcome back!',
          textAlign: wide ? TextAlign.left : TextAlign.center,
          style: theme.textTheme.headlineLarge,
        ),
        const SizedBox(height: 6),
        Text(
          _registering
              ? 'Join ScholarSphere and start your journey toward global '
                    'opportunities.'
              : 'Sign in to continue and discover trusted opportunities.',
          textAlign: wide ? TextAlign.left : TextAlign.center,
          style: theme.textTheme.bodyLarge,
        ),
        const SizedBox(height: 28),
        Container(
          padding: EdgeInsets.all(wide ? 0 : 24),
          decoration: wide
              ? const BoxDecoration()
              : BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: const Color(0xFFE7EAF0)),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.05),
                      blurRadius: 24,
                      offset: const Offset(0, 12),
                    ),
                  ],
                ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildModeToggle(theme),
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
                          return 'Use upper/lowercase, a number, and a '
                              'symbol.';
                        }
                        return null;
                      },
                    ),
                    if (_registering) ...[
                      const SizedBox(height: 8),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          'At least 12 characters with upper/lowercase, a '
                          'number, and a symbol.',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            fontSize: 12,
                            color: const Color(0xFF98A2B3),
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        controlAffinity: ListTileControlAffinity.leading,
                        dense: true,
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
                        controlAffinity: ListTileControlAffinity.leading,
                        dense: true,
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
                _buildErrorBanner(theme),
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
              const SizedBox(height: 4),
              FilledButton(
                key: const Key('auth-submit'),
                onPressed: _busy ? null : _submit,
                child: _busy
                    ? const SizedBox.square(
                        dimension: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : Text(_registering ? 'Create account' : 'Sign in'),
              ),
              const SizedBox(height: 20),
              _buildOrDivider(theme),
              const SizedBox(height: 20),
              OutlinedButton.icon(
                onPressed: _busy ? null : _signInWithGoogle,
                icon: _buildGoogleIcon(),
                label: const Text('Continue with Google'),
              ),
              const SizedBox(height: 20),
              Center(
                child: TextButton(
                  onPressed: _busy ? null : () => _setMode(!_registering),
                  child: Text(
                    _registering
                        ? 'Already have an account? Login'
                        : "Don't have an account? Register now",
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 32),
        _buildTrustBadges(theme),
      ],
    );

    return Center(
      child: SingleChildScrollView(
        padding: EdgeInsets.symmetric(
          horizontal: wide ? 56 : 24,
          vertical: 32,
        ),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: content,
        ),
      ),
    );
  }

  Widget _buildBrandRow(ThemeData theme, {required bool centered}) {
    final primary = theme.colorScheme.primary;
    final row = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: primary.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(Icons.public, color: primary, size: 24),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('ScholarSphere', style: theme.textTheme.titleLarge),
            Text(
              'Opportunities Without Borders',
              style: theme.textTheme.bodyMedium?.copyWith(
                fontSize: 12,
                color: const Color(0xFF98A2B3),
              ),
            ),
          ],
        ),
      ],
    );
    return centered ? Center(child: row) : row;
  }

  Widget _buildModeToggle(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F3F6),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildModeTab(
              theme,
              label: 'Sign in',
              selected: !_registering,
              onTap: () => _setMode(false),
            ),
          ),
          Expanded(
            child: _buildModeTab(
              theme,
              label: 'Register',
              selected: _registering,
              onTap: () => _setMode(true),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildModeTab(
    ThemeData theme, {
    required String label,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: _busy ? null : onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(vertical: 10),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? Colors.white : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.06),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ]
              : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            fontWeight: FontWeight.w700,
            color: selected
                ? theme.colorScheme.primary
                : const Color(0xFF667085),
          ),
        ),
      ),
    );
  }

  Widget _buildErrorBanner(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: theme.colorScheme.error.withValues(alpha: 0.25),
        ),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: theme.colorScheme.error, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              _error!,
              style: TextStyle(color: theme.colorScheme.error),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOrDivider(ThemeData theme) {
    return Row(
      children: [
        const Expanded(child: Divider(color: Color(0xFFE1E6ED))),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Text(
            'or continue with',
            style: theme.textTheme.bodyMedium?.copyWith(
              fontSize: 12,
              color: const Color(0xFF98A2B3),
            ),
          ),
        ),
        const Expanded(child: Divider(color: Color(0xFFE1E6ED))),
      ],
    );
  }

  Widget _buildGoogleIcon() {
    return Container(
      width: 20,
      height: 20,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: const Color(0xFFE1E6ED)),
      ),
      child: const Text(
        'G',
        style: TextStyle(
          fontWeight: FontWeight.w800,
          fontSize: 12,
          color: Color(0xFF4285F4),
        ),
      ),
    );
  }

  Widget _buildTrustBadges(ThemeData theme) {
    final items = [
      (
        Icons.verified_user_outlined,
        'Secure & trusted',
        'Your data is protected with industry-standard security.',
      ),
      (
        Icons.public,
        'Global opportunities',
        'Access scholarships, grants, and internships worldwide.',
      ),
      (
        Icons.groups_outlined,
        'For everyone',
        'Students, professionals, and organizations, all in one place.',
      ),
    ];
    return Wrap(
      spacing: 24,
      runSpacing: 20,
      children: [
        for (final item in items)
          SizedBox(
            width: 220,
            child: _buildBadge(theme, item.$1, item.$2, item.$3),
          ),
      ],
    );
  }

  Widget _buildBadge(
    ThemeData theme,
    IconData icon,
    String title,
    String subtitle,
  ) {
    final primary = theme.colorScheme.primary;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: primary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, size: 18, color: primary),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                style: const TextStyle(
                  fontSize: 12,
                  color: Color(0xFF667085),
                  height: 1.3,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSidePanel(ThemeData theme) {
    const ink = Color(0xFF14213D);
    const teal = Color(0xFF007C72);
    return ClipRect(
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [ink, teal],
          ),
        ),
        child: Stack(
          children: [
            Positioned(
              top: -50,
              left: -50,
              child: _decorativeCircle(140, Colors.white.withValues(alpha: 0.06)),
            ),
            Positioned(
              bottom: -70,
              right: -40,
              child: _decorativeCircle(220, Colors.white.withValues(alpha: 0.06)),
            ),
            Center(
              child: Padding(
                padding: const EdgeInsets.all(48),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 108,
                      height: 108,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white.withValues(alpha: 0.12),
                      ),
                      child: const Icon(
                        Icons.travel_explore,
                        size: 52,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 28),
                    Text(
                      _registering
                          ? 'Join a global community of\nchangemakers.'
                          : 'Discover opportunities\nwithout borders.',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.headlineSmall?.copyWith(
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      _registering
                          ? 'Get personalized recommendations that match '
                                'your goals.'
                          : 'ScholarSphere connects you with verified '
                                'scholarships, grants, and internships.',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyLarge?.copyWith(
                        color: Colors.white.withValues(alpha: 0.8),
                      ),
                    ),
                    const SizedBox(height: 32),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildSideFeature('Verified & trusted platform'),
                          _buildSideFeature('Personalized opportunity matching'),
                          _buildSideFeature('A global network of changemakers'),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _decorativeCircle(double size, Color color) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(shape: BoxShape.circle, color: color),
    );
  }

  Widget _buildSideFeature(String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.check_circle, size: 18, color: Colors.white),
          const SizedBox(width: 10),
          Text(
            text,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
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
