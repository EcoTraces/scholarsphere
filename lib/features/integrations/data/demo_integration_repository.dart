import 'dart:convert';

import '../../audit/domain/audit_record.dart';
import '../../audit/domain/audit_repository.dart';
import '../domain/api_models.dart';
import '../domain/integration_repository.dart';

class DemoIntegrationRepository implements IntegrationRepository {
  DemoIntegrationRepository({
    this.auditRepository,
    DateTime Function()? clock,
    this.rateLimitPerMinute = 60,
  }) : _clock = clock ?? DateTime.now;

  final AuditRepository? auditRepository;
  final DateTime Function() _clock;
  final int rateLimitPerMinute;
  final Map<String, PartnerIntegration> _partners = {};
  final Map<String, ApiKey> _keys = {};
  final Map<String, ApiHandler> _handlers = {};
  final Map<String, ApiEndpointDocumentation> _documentation = {};
  final Map<String, WebhookSubscription> _webhooks = {};
  final Map<String, ApiResponse> _idempotency = {};
  final List<ApiUsageRecord> _usage = [];
  final List<IntegrationDelivery> _deliveries = [];

  @override
  Future<PartnerIntegration> registerPartner(
    PartnerIntegration integration,
  ) async {
    if (_partners.containsKey(integration.id)) {
      throw const IntegrationFailure(
        'duplicate_partner',
        'Partner integration already exists.',
      );
    }
    _partners[integration.id] = integration;
    return integration;
  }

  @override
  Future<IssuedApiKey> issueKey({
    required String partnerId,
    required Set<String> scopes,
    required ApiEnvironment environment,
    DateTime? expiresAt,
  }) async {
    final partner = _partners[partnerId];
    if (partner == null || partner.status != IntegrationStatus.active) {
      throw const IntegrationFailure(
        'partner_inactive',
        'An active partner is required.',
        statusCode: 403,
      );
    }
    if (!partner.scopes.containsAll(scopes)) {
      throw const IntegrationFailure(
        'invalid_scope',
        'Requested scope is not approved for this partner.',
        statusCode: 403,
      );
    }
    final now = _clock();
    final secret =
        'ss_${environment.name}_${now.microsecondsSinceEpoch}_${_keys.length}';
    final key = ApiKey(
      id: 'key-${now.microsecondsSinceEpoch}',
      partnerId: partnerId,
      keyHash: _hash(secret),
      scopes: scopes,
      environment: environment,
      status: ApiKeyStatus.active,
      createdAt: now,
      expiresAt: expiresAt,
    );
    _keys[key.id] = key;
    return IssuedApiKey(key: key, secret: secret);
  }

  @override
  Future<void> revokeKey(String keyId) async {
    final key = _keys[keyId];
    if (key == null) return;
    _keys[keyId] = ApiKey(
      id: key.id,
      partnerId: key.partnerId,
      keyHash: key.keyHash,
      scopes: key.scopes,
      environment: key.environment,
      status: ApiKeyStatus.revoked,
      createdAt: key.createdAt,
      expiresAt: key.expiresAt,
    );
  }

  @override
  Future<void> registerEndpoint(
    ApiEndpointDocumentation documentation,
    ApiHandler handler,
  ) async {
    final key = '${documentation.method.toUpperCase()} ${documentation.path}';
    _documentation[key] = documentation;
    _handlers[key] = handler;
  }

  @override
  Future<ApiResponse> handle(ApiRequest request) async {
    final started = _clock();
    final correlationId =
        request.headers['x-correlation-id'] ??
        'api-${started.microsecondsSinceEpoch}-${_usage.length}';
    var keyId = 'unauthenticated';
    try {
      if (!request.path.startsWith('/api/v1/')) {
        throw const IntegrationFailure(
          'unsupported_version',
          'Only API version v1 is supported.',
          statusCode: 404,
        );
      }
      final rawKey = request.headers['x-api-key'];
      final key = _authenticate(rawKey);
      keyId = key.id;
      _enforceRateLimit(key.id, started);
      final endpointKey = '${request.method.toUpperCase()} ${request.path}';
      final documentation = _documentation[endpointKey];
      final handler = _handlers[endpointKey];
      if (documentation == null || handler == null) {
        throw const IntegrationFailure(
          'endpoint_not_found',
          'The requested endpoint does not exist.',
          statusCode: 404,
        );
      }
      if (!key.scopes.contains(documentation.requiredScope)) {
        throw const IntegrationFailure(
          'forbidden',
          'The API key does not have the required scope.',
          statusCode: 403,
        );
      }
      final idempotencyKey = request.headers['idempotency-key'];
      if (idempotencyKey != null) {
        final cached = _idempotency['${key.id}:$idempotencyKey'];
        if (cached != null) return cached;
      }
      _validatePagination(request.query);
      final data = await handler(request);
      final response = ApiResponse(
        statusCode: 200,
        data: data,
        correlationId: correlationId,
        pagination: _pagination(request.query, data),
        deprecationWarning: documentation.deprecatedAt == null
            ? null
            : 'This endpoint is deprecated'
                  '${documentation.sunsetAt == null ? '.' : ' and sunsets on ${documentation.sunsetAt}.'}',
      );
      if (idempotencyKey != null) {
        _idempotency['${key.id}:$idempotencyKey'] = response;
      }
      await _recordUsage(
        keyId,
        request,
        response.statusCode,
        correlationId,
        started,
      );
      return response;
    } on IntegrationFailure catch (failure) {
      final response = ApiResponse(
        statusCode: failure.statusCode,
        data: null,
        correlationId: correlationId,
        errorCode: failure.code,
        message: failure.message,
      );
      await _recordUsage(
        keyId,
        request,
        response.statusCode,
        correlationId,
        started,
      );
      return response;
    } catch (_) {
      final response = ApiResponse(
        statusCode: 500,
        data: null,
        correlationId: correlationId,
        errorCode: 'integration_error',
        message: 'The integration request could not be completed.',
      );
      await _recordUsage(
        keyId,
        request,
        response.statusCode,
        correlationId,
        started,
      );
      return response;
    }
  }

  @override
  Future<WebhookSubscription> registerWebhook({
    required String partnerId,
    required String url,
    required Set<String> events,
    required String signingSecret,
  }) async {
    final uri = Uri.tryParse(url);
    if (uri == null || uri.scheme != 'https') {
      throw const IntegrationFailure(
        'invalid_webhook_url',
        'Webhook URLs must use HTTPS.',
      );
    }
    final subscription = WebhookSubscription(
      id: 'webhook-${_clock().microsecondsSinceEpoch}',
      partnerId: partnerId,
      url: url,
      events: events,
      signingSecretHash: _hash(signingSecret),
      active: true,
    );
    _webhooks[subscription.id] = subscription;
    return subscription;
  }

  @override
  Future<bool> verifyWebhookSignature({
    required String payload,
    required String signature,
    required String signingSecret,
  }) async => _hash('$signingSecret:$payload') == signature;

  @override
  Future<IntegrationDelivery> deliverWebhook({
    required String subscriptionId,
    required String event,
    required Map<String, Object?> payload,
  }) async {
    final subscription = _webhooks[subscriptionId];
    final success =
        subscription != null &&
        subscription.active &&
        subscription.events.contains(event);
    final delivery = IntegrationDelivery(
      id: 'delivery-${_clock().microsecondsSinceEpoch}-${_deliveries.length}',
      integrationId: subscriptionId,
      event: event,
      status: success ? 'delivered' : 'failed',
      attempts: 1,
      createdAt: _clock(),
      failureReason: success
          ? null
          : 'Webhook is inactive or event is not subscribed.',
    );
    _deliveries.add(delivery);
    return delivery;
  }

  @override
  Future<List<ApiUsageRecord>> usage() async => List.unmodifiable(_usage);

  @override
  Future<List<ApiEndpointDocumentation>> documentation() async =>
      _documentation.values.toList();

  ApiKey _authenticate(String? rawKey) {
    if (rawKey == null) {
      throw const IntegrationFailure(
        'unauthorized',
        'An API key is required.',
        statusCode: 401,
      );
    }
    final hash = _hash(rawKey);
    final matches = _keys.values.where((key) => key.keyHash == hash);
    if (matches.isEmpty) {
      throw const IntegrationFailure(
        'unauthorized',
        'The API key is invalid.',
        statusCode: 401,
      );
    }
    final key = matches.first;
    if (key.status != ApiKeyStatus.active ||
        (key.expiresAt != null && !key.expiresAt!.isAfter(_clock()))) {
      throw const IntegrationFailure(
        'key_inactive',
        'The API key is revoked or expired.',
        statusCode: 401,
      );
    }
    return key;
  }

  void _enforceRateLimit(String keyId, DateTime now) {
    final cutoff = now.subtract(const Duration(minutes: 1));
    final recent = _usage.where(
      (item) => item.apiKeyId == keyId && item.timestamp.isAfter(cutoff),
    );
    if (recent.length >= rateLimitPerMinute) {
      throw const IntegrationFailure(
        'rate_limit_exceeded',
        'API rate limit exceeded.',
        statusCode: 429,
      );
    }
  }

  void _validatePagination(Map<String, String> query) {
    final page = int.tryParse(query['page'] ?? '1') ?? 0;
    final size = int.tryParse(query['page_size'] ?? '20') ?? 0;
    if (page < 1 || size < 1 || size > 100) {
      throw const IntegrationFailure(
        'invalid_pagination',
        'Page must be positive and page size must be from 1 to 100.',
      );
    }
  }

  ApiPagination? _pagination(Map<String, String> query, Object? data) {
    if (data is! List) return null;
    return ApiPagination(
      page: int.parse(query['page'] ?? '1'),
      pageSize: int.parse(query['page_size'] ?? '20'),
      total: data.length,
    );
  }

  Future<void> _recordUsage(
    String keyId,
    ApiRequest request,
    int status,
    String correlationId,
    DateTime started,
  ) async {
    final now = _clock();
    _usage.add(
      ApiUsageRecord(
        apiKeyId: keyId,
        method: request.method,
        path: request.path,
        statusCode: status,
        timestamp: now,
        correlationId: correlationId,
        durationMilliseconds: now.difference(started).inMilliseconds,
      ),
    );
    await auditRepository?.append(
      actorId: keyId,
      actorRole: 'integration',
      action: AuditAction.apiRequest,
      entityType: 'api_endpoint',
      entityId: request.path,
      result: status < 400 ? AuditResult.success : AuditResult.failure,
      failureReason: status < 400 ? null : 'HTTP $status',
      correlationId: correlationId,
      ipAddress: request.ipAddress,
    );
  }

  String _hash(String value) {
    var hash = 0x811c9dc5;
    for (final byte in utf8.encode(value)) {
      hash = ((hash ^ byte) * 0x01000193) & 0x7fffffff;
    }
    return hash.toRadixString(16);
  }
}
