import 'package:flutter/material.dart';

import '../domain/premium_plan.dart';

/// Wraps a premium feature's real UI, showing a locked placeholder (never
/// the feature itself, even partially) when the caller isn't entitled.
///
/// This is a **UI convenience only** - every action the unlocked [child]
/// can trigger must still be independently authorized server-side by the
/// matching backend route's own entitlement check
/// (app/core/entitlements.py::require_entitlement). This widget hiding a
/// button is never the real security boundary, exactly like
/// AccessControlPolicy elsewhere in this app (Coding_Rules.md SS6).
class PremiumFeatureGate extends StatelessWidget {
  const PremiumFeatureGate({
    super.key,
    required this.status,
    required this.featureKey,
    required this.featureLabel,
    required this.child,
    required this.onUnlockPremium,
  });

  final PremiumStatus? status;
  final String featureKey;
  final String featureLabel;
  final Widget child;
  final VoidCallback onUnlockPremium;

  // Checks the union of every active entitlement, not just the most
  // recent one (PremiumStatus.hasFeature) - a caller who bought two
  // separate narrower packages must see both as unlocked here, matching
  // the real backend authorization check
  // (app/core/entitlements.py::has_any_feature).
  bool get _unlocked => status?.hasFeature(featureKey) ?? false;

  @override
  Widget build(BuildContext context) {
    if (_unlocked) return child;

    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(Icons.lock_outline, color: theme.colorScheme.secondary, semanticLabel: 'Locked'),
              const SizedBox(width: 8),
              Text(
                featureLabel,
                style: theme.textTheme.titleLarge,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Premium Feature',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.secondary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: onUnlockPremium,
            child: const Text('Unlock Premium'),
          ),
        ],
      ),
    );
  }
}
