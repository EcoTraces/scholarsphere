import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/premium_plan.dart';
import '../domain/premium_repository.dart';

/// Reads and writes real Premium billing/entitlement data from the
/// ScholarSphere Python backend
/// (app/api/routes/premium_billing.py). Premium status is always the
/// server's answer - this repository never derives `isPremium` from a
/// locally cached flag or a URL parameter (see that route module's own
/// "Payment Security" docstring).
class ApiPremiumRepository implements PremiumRepository {
  ApiPremiumRepository({String? baseUrl, http.Client? client, firebase.FirebaseAuth? auth})
    : baseUrl = baseUrl ?? _defaultBaseUrl,
      _client = client ?? http.Client(),
      _authOverride = auth {
    if (kReleaseMode) {
      TransportSecurityPolicy.requireHttps(Uri.parse(this.baseUrl));
    }
  }

  static const _defaultBaseUrl = String.fromEnvironment(
    'SCHOLARSPHERE_API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  final String baseUrl;
  final http.Client _client;
  final firebase.FirebaseAuth? _authOverride;

  firebase.FirebaseAuth get _auth => _authOverride ?? firebase.FirebaseAuth.instance;

  @override
  Future<List<PremiumPlan>> listPlans() async {
    final body = await _get('/premium/plans') as List<dynamic>;
    return body.map((json) => _toPlan(json as Map<String, dynamic>)).toList();
  }

  @override
  Future<PremiumStatus> getMyStatus() async {
    final body = await _get('/premium/me') as Map<String, dynamic>;
    final entitlementJson = body['entitlement'] as Map<String, dynamic>?;
    return PremiumStatus(
      isPremium: body['is_premium'] as bool,
      entitlement: entitlementJson == null ? null : _toEntitlement(entitlementJson),
      entitlements: (body['entitlements'] as List<dynamic>)
          .map((json) => _toEntitlement(json as Map<String, dynamic>))
          .toList(),
      unlockedFeatures: (body['unlocked_features'] as List<dynamic>).cast<String>(),
      availablePlans: (body['available_plans'] as List<dynamic>)
          .map((json) => _toPlan(json as Map<String, dynamic>))
          .toList(),
    );
  }

  @override
  Future<CheckoutResult> checkout(String planCode) async {
    final body = await _post('/premium/checkout', {'plan_code': planCode}) as Map<String, dynamic>;
    return CheckoutResult(
      payment: _toPayment(body['payment'] as Map<String, dynamic>),
      paymentPublicKey: body['payment_public_key'] as String,
      clientSecret: body['client_secret'] as String?,
      checkoutUrl: body['checkout_url'] as String?,
    );
  }

  @override
  Future<PremiumPayment> verifyPayment(String paymentId) async {
    final body =
        await _post('/premium/payments/$paymentId/verify', const {}) as Map<String, dynamic>;
    return _toPayment(body);
  }

  @override
  Future<List<PremiumPayment>> listMyPayments() async {
    final body = await _get('/premium/payments') as List<dynamic>;
    return body.map((json) => _toPayment(json as Map<String, dynamic>)).toList();
  }

  PremiumPlan _toPlan(Map<String, dynamic> json) => PremiumPlan(
    id: json['id'] as String,
    code: json['code'] as String,
    name: json['name'] as String,
    description: json['description'] as String,
    priceCents: json['price_cents'] as int,
    currency: json['currency'] as String,
    billingInterval: json['billing_interval'] as String,
    features: (json['features'] as List<dynamic>).cast<String>(),
    isActive: json['is_active'] as bool,
  );

  PremiumEntitlement _toEntitlement(Map<String, dynamic> json) => PremiumEntitlement(
    id: json['id'] as String,
    planId: json['plan_id'] as String,
    featureKeys: (json['feature_keys'] as List<dynamic>).cast<String>(),
    status: _entitlementStatusFromWire(json['status'] as String),
    grantedAt: DateTime.parse(json['granted_at'] as String),
    expiresAt: json['expires_at'] == null
        ? null
        : DateTime.parse(json['expires_at'] as String),
  );

  PremiumPayment _toPayment(Map<String, dynamic> json) => PremiumPayment(
    id: json['id'] as String,
    planId: json['plan_id'] as String,
    amountCents: json['amount_cents'] as int,
    currency: json['currency'] as String,
    status: _paymentStatusFromWire(json['status'] as String),
    provider: json['provider'] as String,
    failureReason: json['failure_reason'] as String?,
  );

  static EntitlementStatus _entitlementStatusFromWire(String value) => switch (value) {
    'active' => EntitlementStatus.active,
    'expired' => EntitlementStatus.expired,
    'revoked' => EntitlementStatus.revoked,
    _ => throw LiveBackendException('Unknown entitlement status: $value'),
  };

  static PaymentStatus _paymentStatusFromWire(String value) => switch (value) {
    'pending' => PaymentStatus.pending,
    'processing' => PaymentStatus.processing,
    'success' => PaymentStatus.success,
    'failed' => PaymentStatus.failed,
    'cancelled' => PaymentStatus.cancelled,
    'refunded' => PaymentStatus.refunded,
    'expired' => PaymentStatus.expired,
    'disputed' => PaymentStatus.disputed,
    _ => throw LiveBackendException('Unknown payment status: $value'),
  };

  Future<dynamic> _get(String path) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(() => _client.get(uri, headers: headers));
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(() => _client.post(uri, headers: headers, body: jsonEncode(body)));
  }

  Future<dynamic> _handle(Future<http.Response> Function() request) async {
    late final http.Response response;
    try {
      response = await request();
    } on Exception catch (error) {
      throw LiveBackendException('Could not reach the ScholarSphere backend: $error');
    }
    if (response.statusCode == 401) {
      throw const LiveBackendException('Sign-in expired. Sign in again.', statusCode: 401);
    }
    if (response.statusCode == 402) {
      throw const LiveBackendException(
        'This is a Premium feature. Upgrade to unlock it.',
        statusCode: 402,
      );
    }
    if (response.statusCode == 503) {
      String message = 'Payments are not available right now.';
      try {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        message = (decoded['error'] as Map<String, dynamic>)['message'] as String;
      } on FormatException {
        // Fall back to the generic message above.
      }
      throw LiveBackendException(message, statusCode: 503);
    }
    if (response.statusCode >= 400) {
      throw LiveBackendException(
        'The ScholarSphere backend returned an error.',
        statusCode: response.statusCode,
      );
    }
    if (response.body.isEmpty) return null;
    return jsonDecode(response.body);
  }

  Future<Map<String, String>> _headers() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const LiveBackendException('Sign in first.', statusCode: 401);
    }
    final token = await user.getIdToken();
    return {
      'Authorization': 'Bearer $token',
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
  }

  void dispose() => _client.close();
}
