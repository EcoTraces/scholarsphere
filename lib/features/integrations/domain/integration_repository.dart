import 'api_models.dart';

typedef ApiHandler = Future<Object?> Function(ApiRequest request);

abstract class IntegrationRepository {
  Future<PartnerIntegration> registerPartner(PartnerIntegration integration);
  Future<IssuedApiKey> issueKey({
    required String partnerId,
    required Set<String> scopes,
    required ApiEnvironment environment,
    DateTime? expiresAt,
  });
  Future<void> revokeKey(String keyId);
  Future<void> registerEndpoint(
    ApiEndpointDocumentation documentation,
    ApiHandler handler,
  );
  Future<ApiResponse> handle(ApiRequest request);
  Future<WebhookSubscription> registerWebhook({
    required String partnerId,
    required String url,
    required Set<String> events,
    required String signingSecret,
  });
  Future<bool> verifyWebhookSignature({
    required String payload,
    required String signature,
    required String signingSecret,
  });
  Future<IntegrationDelivery> deliverWebhook({
    required String subscriptionId,
    required String event,
    required Map<String, Object?> payload,
  });
  Future<List<ApiUsageRecord>> usage();
  Future<List<ApiEndpointDocumentation>> documentation();
}

class IntegrationFailure implements Exception {
  const IntegrationFailure(this.code, this.message, {this.statusCode = 400});
  final String code;
  final String message;
  final int statusCode;
}
