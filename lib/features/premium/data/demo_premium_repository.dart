import '../domain/premium_plan.dart';
import '../domain/premium_repository.dart';

/// In-memory demo data - never claims a payment succeeded without an
/// explicit [completeDemoPayment] call, matching this project's standing
/// rule that premium access is only ever granted by a real, verified
/// payment (or, here, an explicit test/demo action standing in for one).
class DemoPremiumRepository implements PremiumRepository {
  DemoPremiumRepository({List<PremiumPlan>? plans})
    : _plans =
          plans ??
          const [
            PremiumPlan(
              id: 'plan-demo-1',
              code: 'complete_premium',
              name: 'Complete Premium Application Package',
              description:
                  'Application strategy, requirement matching, readiness '
                  'scoring, CV builder with ATS optimization, SOP builder, '
                  'study plan builder, research proposal builder, fellowship '
                  'preparation, AI-assisted document improvement, document '
                  'versioning, and PDF/DOCX export.',
              priceCents: 10000,
              currency: 'USD',
              billingInterval: 'one_time',
              features: [
                PremiumFeatureKeys.applicationStrategy,
                PremiumFeatureKeys.requirementMatching,
                PremiumFeatureKeys.readinessScore,
                PremiumFeatureKeys.personalizedChecklist,
                PremiumFeatureKeys.cvBuilder,
                PremiumFeatureKeys.atsOptimization,
                PremiumFeatureKeys.sopBuilder,
                PremiumFeatureKeys.studyPlanBuilder,
                PremiumFeatureKeys.researchProposalBuilder,
                PremiumFeatureKeys.fellowshipPreparation,
                PremiumFeatureKeys.aiDocumentImprovement,
                PremiumFeatureKeys.documentVersioning,
                PremiumFeatureKeys.pdfExport,
                PremiumFeatureKeys.docxExport,
              ],
              isActive: true,
            ),
          ];

  final List<PremiumPlan> _plans;
  PremiumEntitlement? _entitlement;
  final List<PremiumPayment> _payments = [];
  int _paymentCounter = 0;

  @override
  Future<List<PremiumPlan>> listPlans() async =>
      _plans.where((plan) => plan.isActive).toList();

  @override
  Future<PremiumStatus> getMyStatus() async => PremiumStatus(
    isPremium: _entitlement != null,
    entitlement: _entitlement,
    availablePlans: await listPlans(),
  );

  @override
  Future<CheckoutResult> checkout(String planCode) async {
    final plan = _plans.firstWhere(
      (plan) => plan.code == planCode,
      orElse: () => throw StateError('No plan with code $planCode.'),
    );
    _paymentCounter += 1;
    final payment = PremiumPayment(
      id: 'demo-payment-$_paymentCounter',
      planId: plan.id,
      amountCents: plan.priceCents,
      currency: plan.currency,
      status: PaymentStatus.pending,
      provider: 'demo',
    );
    _payments.add(payment);
    // Mirrors the real backend's own honest default (NullPaymentProvider,
    // no PAYMENT_PROVIDER configured): a payment reference is created, but
    // no clientSecret/checkoutUrl is returned until a real provider is
    // wired up. [completeDemoPayment] stands in for what a real provider
    // webhook eventually does.
    return CheckoutResult(payment: payment, paymentPublicKey: '');
  }

  @override
  Future<PremiumPayment> verifyPayment(String paymentId) async {
    final index = _payments.indexWhere((payment) => payment.id == paymentId);
    if (index == -1) {
      throw StateError('Payment $paymentId was not found.');
    }
    return _payments[index];
  }

  @override
  Future<List<PremiumPayment>> listMyPayments() async => List.unmodifiable(_payments);

  /// Test/demo-only helper: simulates a provider webhook confirming
  /// success, mirroring exactly what the real backend does server-side
  /// after real payment verification - never called from any production
  /// code path.
  void completeDemoPayment(String paymentId) {
    final index = _payments.indexWhere((payment) => payment.id == paymentId);
    if (index == -1) return;
    final payment = _payments[index];
    _payments[index] = PremiumPayment(
      id: payment.id,
      planId: payment.planId,
      amountCents: payment.amountCents,
      currency: payment.currency,
      status: PaymentStatus.success,
      provider: payment.provider,
    );
    final plan = _plans.firstWhere((plan) => plan.id == payment.planId);
    _entitlement = PremiumEntitlement(
      id: 'demo-entitlement-1',
      planId: plan.id,
      featureKeys: plan.features,
      status: EntitlementStatus.active,
      grantedAt: DateTime.now(),
      expiresAt: null,
    );
  }
}
