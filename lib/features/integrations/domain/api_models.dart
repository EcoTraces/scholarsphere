enum ApiEnvironment { sandbox, production }

enum ApiKeyStatus { active, revoked, expired }

class ApiKey {
  const ApiKey({
    required this.id,
    required this.partnerId,
    required this.keyHash,
    required this.scopes,
    required this.environment,
    required this.status,
    required this.createdAt,
    this.expiresAt,
  });
  final String id;
  final String partnerId;
  final String keyHash;
  final Set<String> scopes;
  final ApiEnvironment environment;
  final ApiKeyStatus status;
  final DateTime createdAt;
  final DateTime? expiresAt;
}

class IssuedApiKey {
  const IssuedApiKey({required this.key, required this.secret});
  final ApiKey key;
  final String secret;
}

class ApiRequest {
  const ApiRequest({
    required this.method,
    required this.path,
    required this.headers,
    required this.query,
    required this.body,
    required this.ipAddress,
  });
  final String method;
  final String path;
  final Map<String, String> headers;
  final Map<String, String> query;
  final Map<String, Object?> body;
  final String ipAddress;
}

class ApiResponse {
  const ApiResponse({
    required this.statusCode,
    required this.data,
    required this.correlationId,
    this.errorCode,
    this.message,
    this.pagination,
    this.deprecationWarning,
  });
  final int statusCode;
  final Object? data;
  final String correlationId;
  final String? errorCode;
  final String? message;
  final ApiPagination? pagination;
  final String? deprecationWarning;
}

class ApiPagination {
  const ApiPagination({
    required this.page,
    required this.pageSize,
    required this.total,
  });
  final int page;
  final int pageSize;
  final int total;
}

class ApiUsageRecord {
  const ApiUsageRecord({
    required this.apiKeyId,
    required this.method,
    required this.path,
    required this.statusCode,
    required this.timestamp,
    required this.correlationId,
    required this.durationMilliseconds,
  });
  final String apiKeyId;
  final String method;
  final String path;
  final int statusCode;
  final DateTime timestamp;
  final String correlationId;
  final int durationMilliseconds;
}

enum IntegrationStatus { draft, active, suspended, deprecated, retired }

class PartnerIntegration {
  const PartnerIntegration({
    required this.id,
    required this.name,
    required this.scopes,
    required this.environment,
    required this.status,
    required this.createdAt,
    this.contactEmail,
  });
  final String id;
  final String name;
  final Set<String> scopes;
  final ApiEnvironment environment;
  final IntegrationStatus status;
  final DateTime createdAt;
  final String? contactEmail;

  PartnerIntegration copyWith({IntegrationStatus? status}) =>
      PartnerIntegration(
        id: id,
        name: name,
        scopes: scopes,
        environment: environment,
        status: status ?? this.status,
        createdAt: createdAt,
        contactEmail: contactEmail,
      );
}

class WebhookSubscription {
  const WebhookSubscription({
    required this.id,
    required this.partnerId,
    required this.url,
    required this.events,
    required this.signingSecretHash,
    required this.active,
  });
  final String id;
  final String partnerId;
  final String url;
  final Set<String> events;
  final String signingSecretHash;
  final bool active;
}

class IntegrationDelivery {
  const IntegrationDelivery({
    required this.id,
    required this.integrationId,
    required this.event,
    required this.status,
    required this.attempts,
    required this.createdAt,
    this.failureReason,
  });
  final String id;
  final String integrationId;
  final String event;
  final String status;
  final int attempts;
  final DateTime createdAt;
  final String? failureReason;
}

class ApiEndpointDocumentation {
  const ApiEndpointDocumentation({
    required this.method,
    required this.path,
    required this.version,
    required this.requiredScope,
    required this.summary,
    this.deprecatedAt,
    this.sunsetAt,
  });
  final String method;
  final String path;
  final String version;
  final String requiredScope;
  final String summary;
  final DateTime? deprecatedAt;
  final DateTime? sunsetAt;
}
