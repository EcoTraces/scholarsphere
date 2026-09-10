import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mocktail/mocktail.dart';
import 'package:scholarsphere/features/verification/data/api_verification_repository.dart';
import 'package:scholarsphere/features/verification/presentation/live_verification_queue_screen.dart';

class _MockFirebaseAuth extends Mock implements firebase.FirebaseAuth {}

class _MockUser extends Mock implements firebase.User {}

void main() {
  late _MockFirebaseAuth auth;
  late _MockUser user;

  setUp(() {
    auth = _MockFirebaseAuth();
    user = _MockUser();
    when(() => auth.currentUser).thenReturn(user);
    when(() => user.getIdToken()).thenAnswer((_) async => 'test-token');
  });

  Map<String, dynamic> _pendingItemMissingDeadline() => {
    'id': 'opp-no-deadline',
    'title': 'Community Resilience Grant',
    'provider_name': 'Department of Example',
    'opportunity_type': 'grant',
    'country': null,
    'description': null,
    'opening_date': null,
    'deadline': null,
    'official_source_url': 'https://example.test/community-resilience',
    'official_application_url': null,
    'duplicate_review_required': false,
    'collected_at': '2026-01-01T00:00:00Z',
  };

  testWidgets(
    'lists pending records missing a deadline and opens the add-deadline '
    'screen for one',
    (tester) async {
      var patchCalled = false;
      final repository = ApiVerificationRepository(
        baseUrl: 'https://backend.test/api/v1',
        auth: auth,
        client: MockClient((request) async {
          if (request.method == 'PATCH') {
            patchCalled = true;
            return http.Response(
              jsonEncode({
                'id': 'opp-no-deadline',
                'changed_fields': ['deadline'],
              }),
              200,
            );
          }
          return http.Response(
            jsonEncode({
              'items': [_pendingItemMissingDeadline()],
              'total': 1,
              'page': 1,
              'page_size': 100,
            }),
            200,
          );
        }),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: MissingDeadlineQueueScreen(
            repository: repository,
            onSignOut: () {},
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Community Resilience Grant'), findsOneWidget);
      expect(find.text('Nothing is missing a deadline right now.'), findsNothing);

      await tester.tap(find.text('Community Resilience Grant'));
      await tester.pumpAndSettle();

      expect(find.text('Add deadline'), findsOneWidget);
      expect(
        find.text('https://example.test/community-resilience'),
        findsOneWidget,
      );

      // Saving without picking a deadline is rejected client-side, before
      // any network call - never lets an officer save a blank/guessed
      // deadline.
      await tester.tap(find.text('Save deadline'));
      await tester.pumpAndSettle();

      expect(
        find.text('Pick the real deadline from the official source first.'),
        findsOneWidget,
      );
      expect(patchCalled, isFalse);
    },
  );

  testWidgets('shows an empty state when nothing is missing a deadline', (
    tester,
  ) async {
    final repository = ApiVerificationRepository(
      baseUrl: 'https://backend.test/api/v1',
      auth: auth,
      client: MockClient((request) async {
        return http.Response(
          jsonEncode({'items': <dynamic>[], 'total': 0, 'page': 1, 'page_size': 100}),
          200,
        );
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: MissingDeadlineQueueScreen(
          repository: repository,
          onSignOut: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Nothing is missing a deadline right now.'), findsOneWidget);
  });
}
