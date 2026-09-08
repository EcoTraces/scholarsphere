import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/authentication/data/demo_auth_repository.dart';
import 'package:scholarsphere/features/authentication/presentation/auth_screen.dart';
import 'package:scholarsphere/features/governance/data/demo_legal_compliance_repository.dart';
import 'package:scholarsphere/features/governance/domain/legal_compliance.dart';
import 'package:scholarsphere/features/governance/presentation/legal_policy_screen.dart';

void main() {
  Widget buildAuthScreen() => MaterialApp(
    home: AuthScreen(
      repository: DemoAuthRepository(),
      legalRepository: DemoLegalComplianceRepository(),
      onAuthenticated: (_) {},
    ),
  );

  testWidgets('auth screen shows a footer with copyright and legal links', (
    tester,
  ) async {
    await tester.pumpWidget(buildAuthScreen());
    await tester.pumpAndSettle();

    expect(find.textContaining('All rights reserved.'), findsOneWidget);
    expect(find.text('Terms & Conditions'), findsOneWidget);
    expect(find.text('Privacy Policy'), findsOneWidget);
    expect(find.text('Cookie Policy'), findsOneWidget);
    expect(find.textContaining('ecotrace2026@gmail.com'), findsOneWidget);
    expect(find.textContaining('+232395457'), findsWidgets);
  });

  testWidgets('tapping a footer legal link opens the policy screen', (
    tester,
  ) async {
    await tester.pumpWidget(buildAuthScreen());
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Privacy Policy'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Privacy Policy'));
    await tester.pumpAndSettle();

    expect(find.byType(LegalPolicyScreen), findsOneWidget);
    expect(
      find.text('This policy has not been published yet.'),
      findsOneWidget,
    );
  });

  testWidgets(
    'a published policy renders its real content, not a fake placeholder',
    (tester) async {
      final legalRepository = DemoLegalComplianceRepository();
      await legalRepository.publish(
        LegalPolicy(
          id: 'tc-1',
          type: LegalPolicyType.termsAndConditions,
          version: '1.0',
          title: 'Terms & Conditions',
          content: 'The real terms text.',
          effectiveAt: DateTime(2026, 1, 1),
          publishedAt: DateTime(2026, 1, 1),
          requiresAcceptance: true,
          materialChange: false,
          publishedBy: 'system-seed',
        ),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: LegalPolicyScreen(
            repository: legalRepository,
            policyType: LegalPolicyType.termsAndConditions,
            title: 'Terms & Conditions',
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('The real terms text.'), findsOneWidget);
    },
  );
}
