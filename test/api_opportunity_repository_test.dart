import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mocktail/mocktail.dart';
import 'package:scholarsphere/features/opportunities/data/api_opportunity_repository.dart';
import 'package:scholarsphere/features/opportunities/domain/opportunity.dart';

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

  ApiOpportunityRepository repositoryReturning(String type) {
    return ApiOpportunityRepository(
      baseUrl: 'https://backend.test/api/v1',
      auth: auth,
      client: MockClient((request) async {
        return http.Response(
          jsonEncode({
            'items': [
              {
                'id': 'opp-1',
                'title': 'Example opportunity',
                'provider_name': 'Example Institution',
                'opportunity_type': type,
                'country': 'Germany',
                'description': 'An opportunity.',
                'opening_date': '2026-01-01',
                'deadline': '2026-12-31',
                'official_source_url': 'https://example.test/opp-1',
              },
            ],
          }),
          200,
        );
      }),
    );
  }

  test('fellowship records map to OpportunityType.fellowship', () async {
    final opportunities = await repositoryReturning('fellowship').getPublished();
    expect(opportunities.single.type, OpportunityType.fellowship);
  });

  test('scholarship records map to OpportunityType.scholarship', () async {
    final opportunities = await repositoryReturning('scholarship').getPublished();
    expect(opportunities.single.type, OpportunityType.scholarship);
  });

  test('unrecognized types fall back to OpportunityType.grant', () async {
    final opportunities = await repositoryReturning(
      'funding_opportunity',
    ).getPublished();
    expect(opportunities.single.type, OpportunityType.grant);
  });
}
