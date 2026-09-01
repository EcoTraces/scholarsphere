import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/premium/data/demo_premium_repository.dart';
import 'package:scholarsphere/features/premium/presentation/premium_landing_screen.dart';

/// Constructs [PremiumLandingScreen] directly against a
/// [DemoPremiumRepository] rather than through the full `ScholarSphereApp`
/// (test/widget_test.dart's own pattern) - this screen needs no Firebase
/// auth of its own, so a focused, self-contained pump is simpler and keeps
/// this test independent of that large existing file.
void main() {
  testWidgets('shows the real plan price/features and unlocks after a demo payment', (
    tester,
  ) async {
    final repository = DemoPremiumRepository();

    await tester.pumpWidget(
      MaterialApp(home: PremiumLandingScreen(repository: repository)),
    );
    await tester.pumpAndSettle();

    expect(find.text('Complete Premium Application Package'), findsOneWidget);
    expect(find.text(r'$100.00'), findsOneWidget);
    expect(find.text('Unlock Premium'), findsOneWidget);
    expect(find.text('You have ScholarSphere Premium'), findsNothing);

    await tester.tap(find.text('Unlock Premium'));
    await tester.pumpAndSettle();

    // No provider is configured on the demo repository until a payment is
    // explicitly completed - the checkout banner reports that honestly
    // rather than pretending premium unlocked immediately.
    expect(
      find.textContaining('no payment provider is configured'),
      findsOneWidget,
    );

    final payments = await repository.listMyPayments();
    expect(payments, hasLength(1));
    repository.completeDemoPayment(payments.first.id);

    await tester.pumpWidget(
      MaterialApp(home: PremiumLandingScreen(repository: repository)),
    );
    await tester.pumpAndSettle();

    expect(find.text('You have ScholarSphere Premium'), findsOneWidget);
    expect(find.text('Already unlocked'), findsOneWidget);
  });

  testWidgets('shows an empty state when no plans are configured', (tester) async {
    final repository = DemoPremiumRepository(plans: const []);

    await tester.pumpWidget(
      MaterialApp(home: PremiumLandingScreen(repository: repository)),
    );
    await tester.pumpAndSettle();

    expect(find.text('No Premium plans are configured yet.'), findsOneWidget);
  });
}
