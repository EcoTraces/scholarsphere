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
  testWidgets(
    'shows the real plan price/features and unlocks after a demo payment',
    (tester) async {
      final repository = DemoPremiumRepository();

      await tester.pumpWidget(
        MaterialApp(home: PremiumLandingScreen(repository: repository)),
      );
      await tester.pumpAndSettle();

      expect(find.text('Complete Premium Application Package'), findsOneWidget);
      expect(find.text(r'$100.00'), findsOneWidget);
      expect(find.text('Unlock Premium'), findsOneWidget);
      expect(find.text('You have ScholarSphere Premium'), findsNothing);

      // The default test surface (800x600) is shorter than this screen's
      // content, so the button starts off-screen inside the
      // SingleChildScrollView - tap() does not auto-scroll, and tapping an
      // off-screen offset silently misses (a real bug in this test, not the
      // app: it previously tapped nothing and the rest of the test asserted
      // on a screen state that was never actually reached).
      await tester.ensureVisible(find.text('Unlock Premium'));
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

      // Pumping the *same* widget type at the same tree location again
      // does not remount it - Flutter's element reconciliation just
      // updates the existing element in place, so `initState` (and this
      // screen's own one-shot `_load()` call inside it) never re-runs and
      // the screen would keep showing its already-resolved, now-stale
      // status forever. This never actually happens in the real app (the
      // "Premium" entry point uses `Navigator.push`, which always mounts a
      // fresh route/widget), but a widget test has to force the same real
      // remount explicitly by unmounting first.
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpWidget(
        MaterialApp(home: PremiumLandingScreen(repository: repository)),
      );
      await tester.pumpAndSettle();

      expect(find.text('You have ScholarSphere Premium'), findsOneWidget);
      expect(find.text('Already unlocked'), findsOneWidget);
    },
  );

  testWidgets('shows an empty state when no plans are configured', (
    tester,
  ) async {
    final repository = DemoPremiumRepository(plans: const []);

    await tester.pumpWidget(
      MaterialApp(home: PremiumLandingScreen(repository: repository)),
    );
    await tester.pumpAndSettle();

    expect(find.text('No Premium plans are configured yet.'), findsOneWidget);
  });
}
