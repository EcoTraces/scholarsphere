import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/audit/data/demo_audit_repository.dart';
import 'package:scholarsphere/features/audit/domain/audit_record.dart';
import 'package:scholarsphere/features/audit/domain/audit_repository.dart';
import 'package:scholarsphere/features/authentication/domain/user_account.dart';
import 'package:scholarsphere/features/integrations/data/demo_integration_repository.dart';
import 'package:scholarsphere/features/integrations/domain/api_models.dart';

void main() {
  test(
    'audit records are masked, access-controlled, and integrity checked',
    () async {
      var now = DateTime.utc(2026, 7, 29);
      final repository = DemoAuditRepository(clock: () => now);
      await repository.append(
        actorId: 'user-1',
        actorRole: 'applicant',
        action: AuditAction.profileChanged,
        entityType: 'profile',
        entityId: 'profile-1',
        previousValue: 'email=old@example.com password=secret',
        newValue: 'email=new@example.com token=abc123',
        ipAddress: '192.168.1.44',
        result: AuditResult.success,
        correlationId: 'request-1',
      );
      now = now.add(const Duration(minutes: 1));
      await repository.append(
        actorId: 'admin-1',
        actorRole: 'administrator',
        action: AuditAction.dataExported,
        entityType: 'audit',
        entityId: 'all',
        result: AuditResult.success,
        correlationId: 'request-2',
      );

      await expectLater(
        repository.search(UserRole.applicant, const AuditQuery()),
        throwsA(isA<AuditFailure>()),
      );
      final records = await repository.search(
        UserRole.administrator,
        const AuditQuery(action: AuditAction.profileChanged),
      );
      expect(records, hasLength(1));
      expect(records.single.previousValue, contains('[masked-email]'));
      expect(records.single.previousValue, contains('password=***'));
      expect(records.single.ipAddress, '192.168.*.*');
      expect(await repository.verifyIntegrity(), isTrue);
      expect(
        await repository.exportCsv(
          UserRole.securityAdministrator,
          const AuditQuery(),
        ),
        contains('audit_id,actor_id'),
      );
    },
  );

  test(
    'API gateway authenticates, authorizes, and caches idempotent requests',
    () async {
      final repository = DemoIntegrationRepository(
        clock: () => DateTime.utc(2026, 7, 29),
        rateLimitPerMinute: 10,
      );
      await repository.registerPartner(
        PartnerIntegration(
          id: 'partner-1',
          name: 'University Partner',
          scopes: const {'opportunities:read'},
          environment: ApiEnvironment.sandbox,
          status: IntegrationStatus.active,
          createdAt: DateTime.utc(2026, 7, 29),
        ),
      );
      final issued = await repository.issueKey(
        partnerId: 'partner-1',
        scopes: const {'opportunities:read'},
        environment: ApiEnvironment.sandbox,
      );
      var calls = 0;
      await repository.registerEndpoint(
        const ApiEndpointDocumentation(
          method: 'GET',
          path: '/api/v1/opportunities',
          version: 'v1',
          requiredScope: 'opportunities:read',
          summary: 'List opportunities',
        ),
        (request) async {
          calls++;
          return [
            {'id': 'opportunity-1'},
          ];
        },
      );
      final request = ApiRequest(
        method: 'GET',
        path: '/api/v1/opportunities',
        headers: {'x-api-key': issued.secret, 'idempotency-key': 'list-1'},
        query: const {'page': '1', 'page_size': '20', 'sort': 'deadline'},
        body: const {},
        ipAddress: '203.0.113.10',
      );
      final first = await repository.handle(request);
      final second = await repository.handle(request);

      expect(first.statusCode, 200);
      expect(first.pagination?.total, 1);
      expect(second.data, first.data);
      expect(calls, 1);
      expect(
        (await repository.handle(
          const ApiRequest(
            method: 'GET',
            path: '/api/v1/opportunities',
            headers: {},
            query: {},
            body: {},
            ipAddress: '',
          ),
        )).statusCode,
        401,
      );
    },
  );

  test('webhooks require HTTPS and verify signatures', () async {
    final repository = DemoIntegrationRepository();
    final subscription = await repository.registerWebhook(
      partnerId: 'partner-1',
      url: 'https://partner.example/webhooks',
      events: const {'opportunity.verified'},
      signingSecret: 'secret',
    );
    const payload = '{"id":"opportunity-1"}';
    final signature = _hash('secret:$payload');
    expect(
      await repository.verifyWebhookSignature(
        payload: payload,
        signature: signature,
        signingSecret: 'secret',
      ),
      isTrue,
    );
    final delivery = await repository.deliverWebhook(
      subscriptionId: subscription.id,
      event: 'opportunity.verified',
      payload: const {'id': 'opportunity-1'},
    );
    expect(delivery.status, 'delivered');
  });
}

String _hash(String value) {
  var hash = 0x811c9dc5;
  for (final byte in utf8.encode(value)) {
    hash = ((hash ^ byte) * 0x01000193) & 0x7fffffff;
  }
  return hash.toRadixString(16);
}
