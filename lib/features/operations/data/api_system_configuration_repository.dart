import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../authentication/domain/user_account.dart';
import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/system_configuration.dart';
import '../domain/system_configuration_repository.dart';

/// Reads and writes the real platform configuration from the ScholarSphere
/// Python backend. Live replacement for [DemoSystemConfigurationRepository].
///
/// `actor` is accepted on every method for interface compatibility but
/// never sent: authorization and the recorded `updatedBy` are always taken
/// from the caller's own verified auth token server-side.
class ApiSystemConfigurationRepository implements SystemConfigurationRepository {
  ApiSystemConfigurationRepository({
    String? baseUrl,
    http.Client? client,
    firebase.FirebaseAuth? auth,
  }) : baseUrl = baseUrl ?? _defaultBaseUrl,
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

  firebase.FirebaseAuth get _auth =>
      _authOverride ?? firebase.FirebaseAuth.instance;

  @override
  Future<PlatformConfiguration> current() async {
    final body = await _get('/system-configuration/current');
    return _toConfiguration(body as Map<String, dynamic>);
  }

  @override
  Future<PlatformConfiguration> update(
    UserAccount actor,
    PlatformConfiguration configuration,
    String reason,
  ) async {
    try {
      final body = await _put(
        '/system-configuration',
        _toWire(configuration, reason),
      );
      return _toConfiguration(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const ConfigurationFailure(
          'Provider self-publication requires the stronger security policy.',
        );
      }
      if (error.statusCode == 422) {
        throw const ConfigurationFailure('Configuration values are invalid.');
      }
      rethrow;
    }
  }

  @override
  Future<List<PlatformConfiguration>> history(UserAccount actor) async {
    final body = await _get('/system-configuration/history');
    return (body as List<dynamic>)
        .map((item) => _toConfiguration(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<PlatformConfiguration> rollback(
    UserAccount actor,
    int targetVersion,
    String reason,
  ) async {
    try {
      final body = await _post('/system-configuration/rollback', {
        'target_version': targetVersion,
        'reason': reason,
      });
      return _toConfiguration(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const ConfigurationFailure('Configuration version was not found.');
      }
      rethrow;
    }
  }

  Map<String, dynamic> _toWire(
    PlatformConfiguration configuration,
    String reason,
  ) => {
    'platform_name': configuration.platformName,
    'logo_location': configuration.logoLocation,
    'brand_primary_color': configuration.brandPrimaryColor,
    'email_sender_name': configuration.emailSenderName,
    'email_sender_address': configuration.emailSenderAddress,
    'verification_expiration_days': configuration.verificationExpirationDays,
    'supported_countries': configuration.supportedCountries,
    'supported_languages': configuration.supportedLanguages,
    'opportunity_categories': configuration.opportunityCategories,
    'document_types': configuration.documentTypes,
    'maximum_file_size_bytes': configuration.maximumFileSizeBytes,
    'applicant_registration_enabled':
        configuration.applicantRegistrationEnabled,
    'provider_registration_enabled':
        configuration.providerRegistrationEnabled,
    'maintenance_mode': configuration.maintenanceMode,
    'feature_flags': configuration.featureFlags.map(
      (flag, value) => MapEntry(_flagToWire(flag), value),
    ),
    'environment': configuration.environment,
    'security_policy': configuration.securityPolicy,
    'recommendation_settings': configuration.recommendationSettings,
    'fraud_rule_settings': configuration.fraudRuleSettings,
    'integration_settings': configuration.integrationSettings,
    'notification_settings': configuration.notificationSettings,
    'reason': reason,
  };

  PlatformConfiguration _toConfiguration(Map<String, dynamic> json) =>
      PlatformConfiguration(
        version: json['version'] as int,
        platformName: json['platform_name'] as String,
        logoLocation: json['logo_location'] as String,
        brandPrimaryColor: json['brand_primary_color'] as String,
        emailSenderName: json['email_sender_name'] as String,
        emailSenderAddress: json['email_sender_address'] as String,
        verificationExpirationDays:
            json['verification_expiration_days'] as int,
        supportedCountries: (json['supported_countries'] as List<dynamic>)
            .cast<String>(),
        supportedLanguages: (json['supported_languages'] as List<dynamic>)
            .cast<String>(),
        opportunityCategories:
            (json['opportunity_categories'] as List<dynamic>).cast<String>(),
        documentTypes: (json['document_types'] as List<dynamic>)
            .cast<String>(),
        maximumFileSizeBytes: json['maximum_file_size_bytes'] as int,
        applicantRegistrationEnabled:
            json['applicant_registration_enabled'] as bool,
        providerRegistrationEnabled:
            json['provider_registration_enabled'] as bool,
        maintenanceMode: json['maintenance_mode'] as bool,
        featureFlags: (json['feature_flags'] as Map<String, dynamic>).map(
          (key, value) => MapEntry(_flagFromWire(key), value as bool),
        ),
        environment: Map<String, Object>.from(
          json['environment'] as Map<String, dynamic>,
        ),
        securityPolicy: Map<String, Object>.from(
          json['security_policy'] as Map<String, dynamic>,
        ),
        recommendationSettings: Map<String, Object>.from(
          json['recommendation_settings'] as Map<String, dynamic>,
        ),
        fraudRuleSettings: Map<String, Object>.from(
          json['fraud_rule_settings'] as Map<String, dynamic>,
        ),
        integrationSettings: Map<String, Object>.from(
          json['integration_settings'] as Map<String, dynamic>,
        ),
        notificationSettings: Map<String, Object>.from(
          json['notification_settings'] as Map<String, dynamic>,
        ),
        updatedAt: json['updated_at'] == null
            ? null
            : DateTime.parse(json['updated_at'] as String),
        updatedBy: json['updated_by'] as String,
        changeReason: json['change_reason'] as String,
      );

  // Keep in sync with app/schemas/system_configuration.py's flag set.
  static String _flagToWire(FeatureFlag flag) => flag.name;

  static FeatureFlag _flagFromWire(String value) =>
      FeatureFlag.values.firstWhere(
        (flag) => flag.name == value,
        orElse: () => throw LiveBackendException('Unknown feature flag: $value'),
      );

  Future<dynamic> _get(String path) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(() => _client.get(uri, headers: headers));
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.post(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _put(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.put(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _handle(Future<http.Response> Function() request) async {
    late final http.Response response;
    try {
      response = await request();
    } on Exception catch (error) {
      throw LiveBackendException(
        'Could not reach the ScholarSphere backend: $error',
      );
    }
    if (response.statusCode == 401) {
      throw const LiveBackendException(
        'Sign-in expired. Sign in again.',
        statusCode: 401,
      );
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
