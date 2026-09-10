import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mocktail/mocktail.dart';
import 'package:scholarsphere/features/opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import 'package:scholarsphere/features/opportunities/domain/opportunity.dart';
import 'package:scholarsphere/features/verification/data/api_verification_repository.dart';
import 'package:scholarsphere/features/verification/domain/verification_review.dart';

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

  ApiVerificationRepository repositoryFor(
    Future<http.Response> Function(http.Request) handler,
  ) => ApiVerificationRepository(
    baseUrl: 'https://backend.test/api/v1',
    auth: auth,
    client: MockClient(handler),
  );

  test('getQueue maps pending items and requires bearer token', () async {
    late http.Request captured;
    final repository = repositoryFor((request) async {
      captured = request;
      return http.Response(
        jsonEncode({
          'items': [
            {
              'id': 'opp-1',
              'title': 'Community Grant',
              'provider_name': 'Department of Example',
              'opportunity_type': 'grant',
              'country': 'United States',
              'description': 'A grant.',
              'opening_date': '2026-01-01',
              'deadline': '2026-12-31',
              'official_source_url': 'https://example.test/opp-1',
              'official_application_url': 'https://example.test/opp-1/apply',
              'duplicate_review_required': false,
              'collected_at': '2026-01-01T00:00:00Z',
            },
          ],
          'total': 1,
          'page': 1,
          'page_size': 100,
        }),
        200,
      );
    });

    final queue = await repository.getQueue();

    expect(
      captured.url.toString(),
      contains('/external-opportunities/pending-verification'),
    );
    expect(captured.headers['Authorization'], 'Bearer test-token');
    expect(queue, hasLength(1));
    expect(queue.single.title, 'Community Grant');
    expect(queue.single.officialSourceUrl, 'https://example.test/opp-1');
  });

  test(
    'getQueue skips items missing a deadline rather than fabricating one',
    () async {
      final repository = repositoryFor((request) async {
        return http.Response(
          jsonEncode({
            'items': [
              {
                'id': 'opp-2',
                'title': 'No Deadline Grant',
                'provider_name': 'Example Agency',
                'opportunity_type': 'grant',
                'country': null,
                'description': null,
                'opening_date': null,
                'deadline': null,
                'official_source_url': null,
                'official_application_url': null,
                'duplicate_review_required': false,
                'collected_at': '2026-01-01T00:00:00Z',
              },
            ],
            'total': 1,
            'page': 1,
            'page_size': 100,
          }),
          200,
        );
      });

      final queue = await repository.getQueue();

      expect(queue, isEmpty);
    },
  );

  test(
    'getLiveQueue separates reviewable items from ones missing a deadline',
    () async {
      final repository = repositoryFor((request) async {
        return http.Response(
          jsonEncode({
            'items': [
              {
                'id': 'opp-with-deadline',
                'title': 'Has A Deadline',
                'provider_name': 'Example Agency',
                'opportunity_type': 'grant',
                'country': 'Testland',
                'description': 'A grant.',
                'opening_date': '2026-01-01',
                'deadline': '2026-12-31',
                'official_source_url': 'https://example.test/has-deadline',
                'official_application_url': null,
                'duplicate_review_required': false,
                'collected_at': '2026-01-01T00:00:00Z',
              },
              {
                'id': 'opp-no-deadline-1',
                'title': 'No Deadline One',
                'provider_name': 'Example Agency',
                'opportunity_type': 'grant',
                'country': null,
                'description': null,
                'opening_date': null,
                'deadline': null,
                'official_source_url': null,
                'official_application_url': null,
                'duplicate_review_required': false,
                'collected_at': '2026-01-01T00:00:00Z',
              },
              {
                'id': 'opp-no-deadline-2',
                'title': 'No Deadline Two',
                'provider_name': 'Example Agency',
                'opportunity_type': 'grant',
                'country': null,
                'description': null,
                'opening_date': null,
                'deadline': null,
                'official_source_url': null,
                'official_application_url': null,
                'duplicate_review_required': false,
                'collected_at': '2026-01-01T00:00:00Z',
              },
            ],
            'total': 3,
            'page': 1,
            'page_size': 100,
          }),
          200,
        );
      });

      final result = await repository.getLiveQueue();

      expect(result.items, hasLength(1));
      expect(result.items.single.id, 'opp-with-deadline');
      expect(result.missingDeadlineCount, 2);
      expect(
        result.missingDeadlineRecords.map((r) => r.id),
        containsAll(['opp-no-deadline-1', 'opp-no-deadline-2']),
      );
      expect(result.missingDeadlineRecords.first.title, 'No Deadline One');
      expect(result.missingDeadlineRecords.first.provider, 'Example Agency');
    },
  );

  test(
    'getLiveQueue paginates across every page instead of only the first',
    () async {
      var requestCount = 0;
      final repository = repositoryFor((request) async {
        requestCount++;
        final page = request.url.queryParameters['page'];
        // Page 1: 100 items, all missing a deadline (mirrors production,
        // where the most-recently-collected records dominate a
        // recency-sorted first page). Page 2: 1 item with a real deadline -
        // it must still surface, not be lost because the first page filled
        // up on unreviewable records.
        if (page == '1') {
          return http.Response(
            jsonEncode({
              'items': List.generate(
                100,
                (i) => {
                  'id': 'opp-no-deadline-$i',
                  'title': 'No Deadline $i',
                  'provider_name': 'Example Agency',
                  'opportunity_type': 'grant',
                  'country': null,
                  'description': null,
                  'opening_date': null,
                  'deadline': null,
                  'official_source_url': null,
                  'official_application_url': null,
                  'duplicate_review_required': false,
                  'collected_at': '2026-01-01T00:00:00Z',
                },
              ),
              'total': 101,
              'page': 1,
              'page_size': 100,
            }),
            200,
          );
        }
        return http.Response(
          jsonEncode({
            'items': [
              {
                'id': 'opp-reviewable',
                'title': 'Reviewable On Page Two',
                'provider_name': 'Example Agency',
                'opportunity_type': 'grant',
                'country': 'Testland',
                'description': 'A grant.',
                'opening_date': '2026-01-01',
                'deadline': '2026-12-31',
                'official_source_url': 'https://example.test/page-two',
                'official_application_url': null,
                'duplicate_review_required': false,
                'collected_at': '2026-01-02T00:00:00Z',
              },
            ],
            'total': 101,
            'page': 2,
            'page_size': 100,
          }),
          200,
        );
      });

      final result = await repository.getLiveQueue();

      expect(requestCount, 2);
      expect(result.items, hasLength(1));
      expect(result.items.single.id, 'opp-reviewable');
      expect(result.missingDeadlineCount, 100);
    },
  );

  test('submitDecision posts the decision and checklist', () async {
    late http.Request captured;
    final repository = repositoryFor((request) async {
      captured = request;
      return http.Response(
        jsonEncode({
          'id': 'opp-1',
          'verification_status': 'verified',
          'publication_status': 'unpublished',
        }),
        200,
      );
    });

    await repository.submitDecision(
      opportunityId: 'opp-1',
      decision: 'approved',
      notes: 'All checks passed.',
      sourceChecked: true,
      applicationLinkChecked: true,
      deadlineChecked: true,
      duplicateChecked: true,
    );

    expect(captured.method, 'POST');
    expect(
      captured.url.toString(),
      'https://backend.test/api/v1/external-opportunities/opportunities/opp-1/verification',
    );
    final body = jsonDecode(captured.body) as Map<String, dynamic>;
    expect(body['decision'], 'approved');
    expect(body['source_checked'], true);
  });

  test(
    'submitDecision surfaces a 409 checklist conflict as LiveBackendException',
    () async {
      final repository = repositoryFor((request) async {
        return http.Response(
          jsonEncode({
            'detail': 'All verification checks must pass before approval.',
          }),
          409,
        );
      });

      await expectLater(
        repository.submitDecision(
          opportunityId: 'opp-1',
          decision: 'approved',
          notes: 'Missing a check.',
        ),
        throwsA(
          isA<LiveBackendException>().having(
            (error) => error.message,
            'message',
            'All verification checks must pass before approval.',
          ),
        ),
      );
    },
  );

  test('addNote posts the note', () async {
    late http.Request captured;
    final repository = repositoryFor((request) async {
      captured = request;
      return http.Response(
        jsonEncode({
          'id': 'opp-1',
          'verification_status': 'pending',
          'publication_status': 'unpublished',
        }),
        200,
      );
    });

    await repository.addNote('opp-1', 'Called the program office.');

    expect(
      captured.url.toString(),
      'https://backend.test/api/v1/external-opportunities/opportunities/opp-1/notes',
    );
    final body = jsonDecode(captured.body) as Map<String, dynamic>;
    expect(body['note'], 'Called the program office.');
  });

  test(
    'editFields sends only provided fields and returns changed_fields',
    () async {
      late http.Request captured;
      final repository = repositoryFor((request) async {
        captured = request;
        return http.Response(
          jsonEncode({
            'id': 'opp-1',
            'changed_fields': ['title'],
          }),
          200,
        );
      });

      final changed = await repository.editFields(
        opportunityId: 'opp-1',
        reason: 'Official source corrected the title.',
        title: 'Corrected Title',
      );

      expect(captured.method, 'PATCH');
      final body = jsonDecode(captured.body) as Map<String, dynamic>;
      expect(body.keys, containsAll(['reason', 'title']));
      expect(body.containsKey('deadline'), isFalse);
      expect(changed, ['title']);
    },
  );

  test('getReviewState returns null on 404 instead of throwing', () async {
    final repository = repositoryFor((request) async {
      return http.Response(jsonEncode({'detail': 'Not found.'}), 404);
    });

    final review = await repository.getReviewState('opp-missing');

    expect(review, isNull);
  });

  test('getEvidence parses field evidence and raw payload', () async {
    final repository = repositoryFor((request) async {
      return http.Response(
        jsonEncode({
          'opportunity_id': 'opp-1',
          'source_code': 'grants_gov',
          'source_name': 'Grants.gov',
          'source_type': 'government',
          'source_trust_level': 'high',
          'official_source_url': 'https://example.test/opp-1',
          'collected_at': '2026-01-01T00:00:00Z',
          'field_evidence': [
            {'field': 'deadline', 'value': '2026-12-31', 'confidence': 'HIGH'},
          ],
          'raw_payload': {'id': 'opp-1'},
        }),
        200,
      );
    });

    final evidence = await repository.getEvidence('opp-1');

    expect(evidence.sourceName, 'Grants.gov');
    expect(evidence.fieldEvidence.single.field, 'deadline');
    expect(evidence.rawPayload['id'], 'opp-1');
  });

  test(
    'getAwaitingPublication keeps only verified-but-unpublished items',
    () async {
      final repository = repositoryFor((request) async {
        expect(
          request.url.toString(),
          contains('/external-opportunities/opportunities'),
        );
        return http.Response(
          jsonEncode({
            'items': [
              {
                'id': 'opp-verified-unpublished',
                'title': 'Ready to publish',
                'provider_name': 'Ministry of Example',
                'opportunity_type': 'grant',
                'country': 'Sierra Leone',
                'description': 'A grant.',
                'opening_date': '2026-01-01',
                'deadline': '2026-12-31',
                'official_source_url': 'https://example.test/ready',
                'official_application_url': null,
                'duplicate_review_required': false,
                'collected_at': '2026-01-01T00:00:00Z',
                'verification_status': 'verified',
                'publication_status': 'unpublished',
              },
              {
                'id': 'opp-already-published',
                'title': 'Already live',
                'provider_name': 'Ministry of Example',
                'opportunity_type': 'grant',
                'country': 'Sierra Leone',
                'description': 'A grant.',
                'opening_date': '2026-01-01',
                'deadline': '2026-12-31',
                'official_source_url': 'https://example.test/live',
                'official_application_url': null,
                'duplicate_review_required': false,
                'collected_at': '2026-01-01T00:00:00Z',
                'verification_status': 'verified',
                'publication_status': 'published',
              },
              {
                'id': 'opp-still-pending',
                'title': 'Not verified yet',
                'provider_name': 'Ministry of Example',
                'opportunity_type': 'grant',
                'country': 'Sierra Leone',
                'description': 'A grant.',
                'opening_date': '2026-01-01',
                'deadline': '2026-12-31',
                'official_source_url': 'https://example.test/pending',
                'official_application_url': null,
                'duplicate_review_required': false,
                'collected_at': '2026-01-01T00:00:00Z',
                'verification_status': 'pending',
                'publication_status': 'unpublished',
              },
            ],
            'total': 3,
            'page': 1,
            'page_size': 100,
          }),
          200,
        );
      });

      final awaiting = await repository.getAwaitingPublication();

      expect(awaiting, hasLength(1));
      expect(awaiting.single.id, 'opp-verified-unpublished');
      expect(awaiting.single.verificationStatus, VerificationStatus.verified);
    },
  );

  test('setPublished posts the publication decision', () async {
    late http.Request captured;
    final repository = repositoryFor((request) async {
      captured = request;
      return http.Response('', 200);
    });

    await repository.setPublished('opp-1', true);

    expect(
      captured.url.toString(),
      contains('/external-opportunities/opportunities/opp-1/publication'),
    );
    expect(captured.method, 'POST');
    expect(jsonDecode(captured.body), {'published': true});
  });

  test('throws when no user is signed in', () async {
    when(() => auth.currentUser).thenReturn(null);
    final repository = repositoryFor((request) async {
      fail('should not make a network request without a signed-in user');
    });

    await expectLater(
      repository.getQueue(),
      throwsA(isA<LiveBackendException>()),
    );
  });

  group('unsupported two-person-workflow methods throw clearly', () {
    late ApiVerificationRepository repository;

    setUp(() {
      repository = repositoryFor((request) async {
        fail('should not make a network request');
      });
    });

    test('getLatestReview', () {
      expect(() => repository.getLatestReview('opp-1'), throwsUnsupportedError);
    });

    test('submitReview', () {
      final review = VerificationReview(
        opportunityId: 'opp-1',
        sourceAuthority: SourceAuthority.unverifiedThirdParty,
        checklist: const VerificationChecklist(),
        status: VerificationStatus.pending,
        notes: '',
        reviewedByUserId: 'officer-1',
        reviewedAt: DateTime(2026, 1, 1),
        nextReviewAt: null,
      );
      expect(() => repository.submitReview(review), throwsUnsupportedError);
    });

    test('assign', () {
      expect(
        () => repository.assign(
          opportunityId: 'opp-1',
          officerId: 'officer-1',
          assignedByUserId: 'officer-2',
        ),
        throwsUnsupportedError,
      );
    });

    test('getHistory', () {
      expect(() => repository.getHistory('opp-1'), throwsUnsupportedError);
    });

    test('getAllForAdministration', () {
      expect(
        () => repository.getAllForAdministration(),
        throwsUnsupportedError,
      );
    });
  });
}
