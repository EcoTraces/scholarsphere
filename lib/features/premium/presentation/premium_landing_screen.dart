import 'package:flutter/material.dart';

import '../../opportunities/data/api_opportunity_repository.dart' show LiveBackendException;
import '../domain/premium_plan.dart';
import '../domain/premium_repository.dart';

/// Premium landing/pricing/checkout screen. Every price and feature shown
/// here comes from [PremiumRepository.listPlans]/[getMyStatus] - never a
/// hardcoded "$100" (see the platform spec's "Premium Business Model"
/// section) - and premium status is always the server's own answer, never
/// a locally-cached flag.
class PremiumLandingScreen extends StatefulWidget {
  const PremiumLandingScreen({super.key, required this.repository});

  final PremiumRepository repository;

  @override
  State<PremiumLandingScreen> createState() => _PremiumLandingScreenState();
}

class _PremiumLandingScreenState extends State<PremiumLandingScreen> {
  late Future<PremiumStatus> _status;
  bool _checkoutInFlight = false;
  String? _checkoutMessage;
  bool _checkoutIsError = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _status = widget.repository.getMyStatus();
  }

  Future<void> _unlock(PremiumPlan plan) async {
    setState(() {
      _checkoutInFlight = true;
      _checkoutMessage = null;
      _checkoutIsError = false;
    });
    try {
      final result = await widget.repository.checkout(plan.code);
      if (!mounted) return;
      setState(() {
        _checkoutInFlight = false;
        if (result.clientSecret != null || result.checkoutUrl != null) {
          _checkoutMessage =
              'Checkout started (payment reference ${result.payment.id}). '
              'Complete payment through the configured provider to unlock Premium.';
        } else {
          _checkoutMessage =
              'A payment reference was created (${result.payment.id}), but no '
              'payment provider is configured yet. An administrator needs to '
              'set PAYMENT_PROVIDER and its credentials before real payments '
              'can be completed.';
        }
      });
    } on LiveBackendException catch (error) {
      if (!mounted) return;
      setState(() {
        _checkoutInFlight = false;
        _checkoutIsError = true;
        _checkoutMessage = error.message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('ScholarSphere Premium')),
      body: FutureBuilder<PremiumStatus>(
        future: _status,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return _ErrorState(onRetry: () => setState(_load));
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final status = snapshot.data!;
          return LayoutBuilder(
            builder: (context, constraints) {
              final wide = constraints.maxWidth >= 720;
              return SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 960),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _Hero(status: status),
                      const SizedBox(height: 24),
                      if (status.availablePlans.isEmpty)
                        const _EmptyPlansState()
                      else
                        Wrap(
                          spacing: 20,
                          runSpacing: 20,
                          children: status.availablePlans
                              .map(
                                (plan) => SizedBox(
                                  width: wide
                                      ? (constraints.maxWidth - 20) / 2
                                      : constraints.maxWidth,
                                  child: _PlanCard(
                                    plan: plan,
                                    isOwned:
                                        status.entitlement != null &&
                                        status.entitlement!.planId == plan.id,
                                    inFlight: _checkoutInFlight,
                                    onUnlock: () => _unlock(plan),
                                  ),
                                ),
                              )
                              .toList(),
                        ),
                      if (_checkoutMessage != null) ...[
                        const SizedBox(height: 20),
                        _CheckoutStatusBanner(
                          message: _checkoutMessage!,
                          isError: _checkoutIsError,
                        ),
                      ],
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.status});

  final PremiumStatus status;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (status.isPremium) {
      final expiresAt = status.entitlement?.expiresAt;
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: theme.colorScheme.primaryContainer,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            Icon(Icons.verified, color: theme.colorScheme.primary, semanticLabel: 'Premium active'),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('You have ScholarSphere Premium', style: theme.textTheme.titleLarge),
                  const SizedBox(height: 4),
                  Text(
                    expiresAt == null
                        ? 'Lifetime access to every Premium feature.'
                        : 'Access until ${expiresAt.toLocal()}'.split('.').first,
                    style: theme.textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Prepare a stronger application', style: theme.textTheme.headlineSmall),
        const SizedBox(height: 8),
        Text(
          'CV and ATS optimization, SOP and study plan builders, research '
          'proposal support, fellowship preparation, requirement matching, '
          'and an honest readiness score - built from your own real profile '
          'and background, never invented.',
          style: theme.textTheme.bodyLarge,
        ),
      ],
    );
  }
}

class _PlanCard extends StatelessWidget {
  const _PlanCard({
    required this.plan,
    required this.isOwned,
    required this.inFlight,
    required this.onUnlock,
  });

  final PremiumPlan plan;
  final bool isOwned;
  final bool inFlight;
  final VoidCallback onUnlock;

  static const _featureLabels = {
    PremiumFeatureKeys.applicationStrategy: 'Application strategy',
    PremiumFeatureKeys.requirementMatching: 'Requirement matching',
    PremiumFeatureKeys.readinessScore: 'Application readiness score',
    PremiumFeatureKeys.personalizedChecklist: 'Personalized checklist',
    PremiumFeatureKeys.cvBuilder: 'CV builder',
    PremiumFeatureKeys.atsOptimization: 'ATS optimization',
    PremiumFeatureKeys.sopBuilder: 'SOP / personal statement builder',
    PremiumFeatureKeys.studyPlanBuilder: 'Study plan builder',
    PremiumFeatureKeys.researchProposalBuilder: 'Research proposal builder',
    PremiumFeatureKeys.fellowshipPreparation: 'Fellowship preparation',
    PremiumFeatureKeys.aiDocumentImprovement: 'AI-assisted document improvement',
    PremiumFeatureKeys.documentVersioning: 'Document versioning',
    PremiumFeatureKeys.pdfExport: 'PDF export',
    PremiumFeatureKeys.docxExport: 'DOCX export',
  };

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(plan.name, style: theme.textTheme.titleLarge),
            const SizedBox(height: 4),
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Text(
                  plan.displayPrice,
                  style: theme.textTheme.headlineLarge,
                ),
                const SizedBox(width: 6),
                Text(
                  plan.billingInterval == 'one_time' ? 'one-time' : 'per ${plan.billingInterval}',
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (plan.description.isNotEmpty) Text(plan.description, style: theme.textTheme.bodyMedium),
            const SizedBox(height: 16),
            ...plan.features.map(
              (feature) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  children: [
                    Icon(Icons.check_circle, size: 18, color: theme.colorScheme.primary),
                    const SizedBox(width: 8),
                    Expanded(child: Text(_featureLabels[feature] ?? feature)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: isOwned || inFlight ? null : onUnlock,
                child: inFlight
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(isOwned ? 'Already unlocked' : 'Unlock Premium'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CheckoutStatusBanner extends StatelessWidget {
  const _CheckoutStatusBanner({required this.message, required this.isError});

  final String message;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = isError ? theme.colorScheme.error : theme.colorScheme.primary;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border.all(color: color),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            isError ? Icons.error_outline : Icons.info_outline,
            color: color,
            semanticLabel: isError ? 'Error' : 'Information',
          ),
          const SizedBox(width: 10),
          Expanded(child: Text(message)),
        ],
      ),
    );
  }
}

class _EmptyPlansState extends StatelessWidget {
  const _EmptyPlansState();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 32),
      child: Center(
        child: Column(
          children: [
            Icon(Icons.inventory_2_outlined, size: 40, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: 12),
            const Text('No Premium plans are configured yet.'),
          ],
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: 40, color: Theme.of(context).colorScheme.error),
            const SizedBox(height: 12),
            const Text("We couldn't load Premium plans."),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
