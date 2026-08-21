// Temporary visual-verification harness for the form redesign pass.
// Not part of the app's real test suite -- deleted after use.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/app/theme.dart';
import 'package:scholarsphere/features/authentication/data/demo_auth_repository.dart';
import 'package:scholarsphere/features/authentication/domain/user_account.dart';
import 'package:scholarsphere/features/authentication/presentation/auth_screen.dart';
import 'package:scholarsphere/features/profiles/data/demo_applicant_profile_repository.dart';
import 'package:scholarsphere/features/profiles/presentation/applicant_profile_screen.dart';
import 'package:scholarsphere/features/provider_analytics/data/demo_provider_analytics_repository.dart';
import 'package:scholarsphere/features/providers/data/demo_provider_repository.dart';
import 'package:scholarsphere/features/providers/presentation/provider_account_screen.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';

const _outDir =
    r'C:\Users\FATMAT~1.KAM\AppData\Local\Temp\claude\c--Users-Fatmata-Z--Kamara-scholarsphere\4390280a-00a4-4812-9edd-b0d9d6856964\scratchpad';

Widget _boundary(GlobalKey key, Widget child) =>
    RepaintBoundary(key: key, child: child);

Future<void> _shoot(WidgetTester tester, GlobalKey key, String name) async {
  final boundary =
      key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
  final image = await boundary.toImage(pixelRatio: 1.5);
  final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
  final file = File('$_outDir\\$name.png');
  await file.writeAsBytes(bytes!.buffer.asUint8List());
}

void main() {
  testWidgets('screenshot: sign-up form with partial password', (tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final authRepository = DemoAuthRepository(
      bootstrapAdminEmail: 'admin@scholarsphere.test',
      bootstrapAdminPassword: 'Admin123!',
    );
    final key = GlobalKey();

    await tester.pumpWidget(
      _boundary(
        key,
        MaterialApp(
          theme: buildScholarSphereTheme(),
          home: AuthScreen(
            repository: authRepository,
            onAuthenticated: (_) {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Switch to Register mode.
    await tester.tap(find.text('Register'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const Key('auth-email')),
      'new.user@example.com',
    );
    await tester.enterText(
      find.byKey(const Key('auth-password')),
      'Password1', // meets length+upper+lower+number, missing symbol
    );
    await tester.pump();

    await _shoot(tester, key, 'auth_register_password_checklist');
  });

  testWidgets('screenshot: provider registration form sections', (tester) async {
    tester.view.physicalSize = const Size(1280, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    const user = UserAccount(
      id: 'user-1',
      fullName: 'Jordan Rivers',
      email: 'jordan@example.com',
      role: UserRole.opportunityProvider,
      status: AccountStatus.active,
      emailVerified: true,
    );

    final key = GlobalKey();
    await tester.pumpWidget(
      _boundary(
        key,
        MaterialApp(
          theme: buildScholarSphereTheme(),
          home: ProviderAccountScreen(
            user: user,
            providerRepository: DemoProviderRepository(),
            opportunityRepository: DemoOpportunityRepository(),
            analyticsRepository: DemoProviderAnalyticsRepository(),
            onSignOut: () {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await _shoot(tester, key, 'provider_registration_sections');
  });

  testWidgets('screenshot: applicant profile required legend + save', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1000, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    const user = UserAccount(
      id: 'user-2',
      fullName: 'Amara Chen',
      email: 'amara@example.com',
      role: UserRole.applicant,
      status: AccountStatus.active,
      emailVerified: true,
    );

    final key = GlobalKey();
    await tester.pumpWidget(
      _boundary(
        key,
        MaterialApp(
          theme: buildScholarSphereTheme(),
          home: ApplicantProfileScreen(
            user: user,
            repository: DemoApplicantProfileRepository(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await _shoot(tester, key, 'applicant_profile_legend_save');
  });
}
