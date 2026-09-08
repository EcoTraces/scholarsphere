import 'package:flutter/material.dart';

import '../domain/legal_compliance.dart';
import '../domain/legal_compliance_repository.dart';

/// A public, sign-in-free viewer for a single legal policy (Terms &
/// Conditions, Privacy Policy, Cookie Policy, ...). Reached from the
/// [AppFooter] on the pre-login auth screen and from the registration
/// form's own consent checkboxes, so a visitor can read what they're
/// agreeing to before creating an account.
class LegalPolicyScreen extends StatefulWidget {
  const LegalPolicyScreen({
    super.key,
    required this.repository,
    required this.policyType,
    required this.title,
  });

  final LegalComplianceRepository repository;
  final LegalPolicyType policyType;
  final String title;

  @override
  State<LegalPolicyScreen> createState() => _LegalPolicyScreenState();
}

class _LegalPolicyScreenState extends State<LegalPolicyScreen> {
  late Future<LegalPolicy?> _policy;

  @override
  void initState() {
    super.initState();
    _policy = widget.repository.current(widget.policyType);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: FutureBuilder<LegalPolicy?>(
        future: _policy,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.error_outline,
                      size: 40,
                      color: Theme.of(context).colorScheme.error,
                    ),
                    const SizedBox(height: 12),
                    const Text('This policy could not be loaded.'),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: () => setState(
                        () => _policy = widget.repository.current(
                          widget.policyType,
                        ),
                      ),
                      icon: const Icon(Icons.refresh),
                      label: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            );
          }
          final policy = snapshot.data;
          if (policy == null) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('This policy has not been published yet.'),
              ),
            );
          }
          return SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 720),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      policy.title,
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Version ${policy.version} · '
                      'Effective ${_formatDate(policy.effectiveAt)}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: const Color(0xFF667085),
                      ),
                    ),
                    const SizedBox(height: 24),
                    Text(
                      policy.content,
                      style: Theme.of(
                        context,
                      ).textTheme.bodyLarge?.copyWith(height: 1.6),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

String _formatDate(DateTime date) =>
    '${date.day.toString().padLeft(2, '0')}/'
    '${date.month.toString().padLeft(2, '0')}/'
    '${date.year}';
