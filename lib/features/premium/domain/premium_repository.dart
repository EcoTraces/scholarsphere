import 'premium_plan.dart';

abstract class PremiumRepository {
  Future<List<PremiumPlan>> listPlans();
  Future<PremiumStatus> getMyStatus();
  Future<CheckoutResult> checkout(String planCode);
  Future<PremiumPayment> verifyPayment(String paymentId);
  Future<List<PremiumPayment>> listMyPayments();
}
