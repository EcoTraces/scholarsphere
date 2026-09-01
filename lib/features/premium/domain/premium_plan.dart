/// Mirrors app/models/premium_billing.py's PremiumPlan/Entitlement/Payment
/// shape exactly - prices and feature lists are never hardcoded in the
/// Flutter client, always read from the backend's own admin-configurable
/// `premium_plans` table.
class PremiumPlan {
  const PremiumPlan({
    required this.id,
    required this.code,
    required this.name,
    required this.description,
    required this.priceCents,
    required this.currency,
    required this.billingInterval,
    required this.features,
    required this.isActive,
  });

  final String id;
  final String code;
  final String name;
  final String description;
  final int priceCents;
  final String currency;
  final String billingInterval;
  final List<String> features;
  final bool isActive;

  /// A locale-agnostic "$100.00"-style display string - real formatting
  /// (currency symbol placement, thousands separators) is deliberately
  /// simple here; a future pass can add `intl`-based formatting once a
  /// real locale requirement exists, per this project's own
  /// "no premature generality" rule.
  String get displayPrice {
    final amount = (priceCents / 100).toStringAsFixed(2);
    final symbol = currency == 'USD' ? r'$' : '$currency ';
    return '$symbol$amount';
  }
}

enum EntitlementStatus { active, expired, revoked }

class PremiumEntitlement {
  const PremiumEntitlement({
    required this.id,
    required this.planId,
    required this.featureKeys,
    required this.status,
    required this.grantedAt,
    required this.expiresAt,
  });

  final String id;
  final String planId;
  final List<String> featureKeys;
  final EntitlementStatus status;
  final DateTime grantedAt;
  final DateTime? expiresAt;

  bool hasFeature(String featureKey) => featureKeys.contains(featureKey);
}

class PremiumStatus {
  const PremiumStatus({
    required this.isPremium,
    required this.entitlement,
    required this.availablePlans,
  });

  final bool isPremium;
  final PremiumEntitlement? entitlement;
  final List<PremiumPlan> availablePlans;
}

enum PaymentStatus {
  pending,
  processing,
  success,
  failed,
  cancelled,
  refunded,
  expired,
  disputed,
}

class PremiumPayment {
  const PremiumPayment({
    required this.id,
    required this.planId,
    required this.amountCents,
    required this.currency,
    required this.status,
    required this.provider,
    this.failureReason,
  });

  final String id;
  final String planId;
  final int amountCents;
  final String currency;
  final PaymentStatus status;
  final String provider;
  final String? failureReason;
}

/// The result of initiating checkout - `checkoutUrl`/`clientSecret` are
/// only present once a real payment provider is configured server-side;
/// `paymentPublicKey` is safe to hand to a client-side payment SDK (it is
/// never the provider's secret key - see
/// app/services/payment_provider.py's own docstring on this distinction).
class CheckoutResult {
  const CheckoutResult({
    required this.payment,
    required this.paymentPublicKey,
    this.clientSecret,
    this.checkoutUrl,
  });

  final PremiumPayment payment;
  final String paymentPublicKey;
  final String? clientSecret;
  final String? checkoutUrl;
}

/// Named feature keys, kept in sync with
/// app/models/premium_billing.py::PremiumFeature. Used by
/// [PremiumFeatureGate] to check whether a specific premium capability is
/// unlocked, never a bare `isPremium` boolean.
abstract final class PremiumFeatureKeys {
  static const applicationStrategy = 'application_strategy';
  static const requirementMatching = 'requirement_matching';
  static const readinessScore = 'readiness_score';
  static const personalizedChecklist = 'personalized_checklist';
  static const cvBuilder = 'cv_builder';
  static const atsOptimization = 'ats_optimization';
  static const sopBuilder = 'sop_builder';
  static const studyPlanBuilder = 'study_plan_builder';
  static const researchProposalBuilder = 'research_proposal_builder';
  static const fellowshipPreparation = 'fellowship_preparation';
  static const aiDocumentImprovement = 'ai_document_improvement';
  static const documentVersioning = 'document_versioning';
  static const pdfExport = 'pdf_export';
  static const docxExport = 'docx_export';
}
