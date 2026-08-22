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

  Map<String, dynamic> _adminItem(String id, String verificationStatus) => {
    'id': id,
    'title': 'Example opportunity $id',
    'provider_name': 'Example Institution',
    'opportunity_type': 'grant',
    'country': 'Germany',
    'description': 'An opportunity.',
    'opening_date': '2026-01-01',
    'deadline': '2026-12-31',
    'official_source_url': 'https://example.test/$id',
    'verification_status': verificationStatus,
  };

  test(
    'getAllForAdministration maps every verification status and stops '
    'once every page has been fetched',
    () async {
      var requestCount = 0;
      final repository = ApiOpportunityRepository(
        baseUrl: 'https://backend.test/api/v1',
        auth: auth,
        client: MockClient((request) async {
          requestCount += 1;
          expect(
            request.url.path,
            '/api/v1/external-opportunities/opportunities',
          );
          expect(request.url.queryParameters['page'], '1');
          return http.Response(
            jsonEncode({
              'items': [
                _adminItem('opp-pending', 'pending'),
                _adminItem('opp-verified', 'verified'),
                _adminItem('opp-rejected', 'rejected'),
                _adminItem('opp-suspicious', 'suspicious'),
                _adminItem('opp-expired', 'expired'),
                _adminItem('opp-archived', 'archived'),
                _adminItem('opp-reverify', 'reverification_required'),
                _adminItem('opp-unavailable', 'source_unavailable'),
              ],
              'total': 8,
            }),
            200,
          );
        }),
      );

      final opportunities = await repository.getAllForAdministration();

      expect(requestCount, 1);
      expect(opportunities, hasLength(8));
      final byId = {for (final item in opportunities) item.id: item};
      expect(
        byId['opp-pending']!.verificationStatus,
        VerificationStatus.pending,
      );
      expect(
        byId['opp-verified']!.verificationStatus,
        VerificationStatus.verified,
      );
      expect(
        byId['opp-rejected']!.verificationStatus,
        VerificationStatus.rejected,
      );
      expect(
        byId['opp-suspicious']!.verificationStatus,
        VerificationStatus.suspicious,
      );
      expect(
        byId['opp-expired']!.verificationStatus,
        VerificationStatus.expired,
      );
      expect(
        byId['opp-archived']!.verificationStatus,
        VerificationStatus.archived,
      );
      expect(
        byId['opp-reverify']!.verificationStatus,
        VerificationStatus.verificationExpired,
      );
      expect(
        byId['opp-unavailable']!.verificationStatus,
        VerificationStatus.incomplete,
      );
    },
  );
}
