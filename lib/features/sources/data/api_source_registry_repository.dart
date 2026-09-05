import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/source_record.dart';
import '../domain/source_registry_repository.dart';

/// Reads and writes real source-registry governance data (staff-curated
/// trust review of external opportunity sources) from the ScholarSphere
/// Python backend. This is the live replacement for
/// [DemoSourceRegistryRepository]; it is unrelated to the separate,
/// already-real ingestion-pipeline source bookkeeping the sync pipeline
/// uses internally.
class ApiSourceRegistryRepository implements SourceRegistryRepository {
  ApiSourceRegistryRepository({
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
  Future<List<SourceRecord>> getAll() async {
    final body = await _get('/source-registry');
    return (body as List<dynamic>)
        .map((item) => _toRecord(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<SourceRecord> register(SourceRecord source) async {
    try {
      final body = await _post('/source-registry', {
        'id': source.id,
        'name': source.name,
        'type': _typeToWire(source.type),
        'domain': source.domain,
        'country': source.country,
        'organization_id': source.organizationId,
        'trust_level': _levelToWire(source.trustLevel),
        'accuracy_rate': source.accuracyRate,
        'parser_configuration': source.parserConfiguration,
      });
      return _toRecord(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const SourceRegistryFailure(
          'This source domain is already registered.',
        );
      }
      if (error.statusCode == 422) {
        throw const SourceRegistryFailure('A valid source domain is required.');
      }
      rethrow;
    }
  }

  @override
  Future<SourceRecord> review({
    required String sourceId,
    required ReliabilityLevel trustLevel,
    required SourceVerificationStatus status,
  }) async {
    try {
      final body = await _post('/source-registry/$sourceId/review', {
        'trust_level': _levelToWire(trustLevel),
        'status': _statusToWire(status),
      });
      return _toRecord(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const SourceRegistryFailure('Source was not found.');
      }
      rethrow;
    }
  }

  @override
  Future<SourceRecord?> approvedSourceFor(String location) async {
    final body = await _get('/source-registry/approved', {
      'location': location,
    });
    if (body == null) return null;
    return _toRecord(body as Map<String, dynamic>);
  }

  @override
  Future<SourceRecord> recordAccess(
    String sourceId, {
    required bool successful,
  }) async {
    try {
      final body = await _post('/source-registry/$sourceId/access', {
        'successful': successful,
      });
      return _toRecord(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const SourceRegistryFailure('Source was not found.');
      }
      rethrow;
    }
  }

  @override
  Future<SourceRecord> recordCorrection(String sourceId) async {
    try {
      final body = await _post(
        '/source-registry/$sourceId/correction',
        const {},
      );
      return _toRecord(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const SourceRegistryFailure('Source was not found.');
      }
      rethrow;
    }
  }

  SourceRecord _toRecord(Map<String, dynamic> json) => SourceRecord(
    id: json['id'] as String,
    name: json['name'] as String,
    type: _typeFromWire(json['type'] as String),
    domain: json['domain'] as String,
    country: json['country'] as String,
    organizationId: json['organization_id'] as String,
    trustLevel: _levelFromWire(json['trust_level'] as String),
    trustScore: json['trust_score'] as int,
    verificationStatus: _statusFromWire(json['verification_status'] as String),
    lastCheckedAt: _dateTime(json['last_checked_at']),
    lastSuccessfulAccess: _dateTime(json['last_successful_access']),
    accuracyRate: (json['accuracy_rate'] as num).toDouble(),
    correctionCount: json['correction_count'] as int,
    rejectionCount: json['rejection_count'] as int,
    isBlocked: json['is_blocked'] as bool,
    createdAt: DateTime.parse(json['created_at'] as String),
    updatedAt: DateTime.parse(json['updated_at'] as String),
    expiresAt: _dateTime(json['expires_at']),
    parserConfiguration: (json['parser_configuration'] as Map<String, dynamic>?)
        ?.cast<String, String>(),
  );

  static DateTime? _dateTime(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  // Keep in sync with app/schemas/source_registry.py's wire map.
  static String _typeToWire(OpportunitySourceType type) => switch (type) {
    OpportunitySourceType.officialUniversityWebsite =>
      'officialUniversityWebsite',
    OpportunitySourceType.officialGovernmentPortal =>
      'officialGovernmentPortal',
    OpportunitySourceType.embassyWebsite => 'embassyWebsite',
    OpportunitySourceType.foundationWebsite => 'foundationWebsite',
    OpportunitySourceType.internationalOrganization =>
      'internationalOrganization',
    OpportunitySourceType.officialApplicationPortal =>
      'officialApplicationPortal',
    OpportunitySourceType.approvedApi => 'approvedApi',
    OpportunitySourceType.approvedRssFeed => 'approvedRssFeed',
    OpportunitySourceType.verifiedProviderSubmission =>
      'verifiedProviderSubmission',
    OpportunitySourceType.trustedSecondarySource => 'trustedSecondarySource',
    OpportunitySourceType.communitySubmission => 'communitySubmission',
  };

  static OpportunitySourceType _typeFromWire(String value) => switch (value) {
    'officialUniversityWebsite' =>
      OpportunitySourceType.officialUniversityWebsite,
    'officialGovernmentPortal' =>
      OpportunitySourceType.officialGovernmentPortal,
    'embassyWebsite' => OpportunitySourceType.embassyWebsite,
    'foundationWebsite' => OpportunitySourceType.foundationWebsite,
    'internationalOrganization' =>
      OpportunitySourceType.internationalOrganization,
    'officialApplicationPortal' =>
      OpportunitySourceType.officialApplicationPortal,
    'approvedApi' => OpportunitySourceType.approvedApi,
    'approvedRssFeed' => OpportunitySourceType.approvedRssFeed,
    'verifiedProviderSubmission' =>
      OpportunitySourceType.verifiedProviderSubmission,
    'trustedSecondarySource' => OpportunitySourceType.trustedSecondarySource,
    'communitySubmission' => OpportunitySourceType.communitySubmission,
    _ => throw LiveBackendException('Unknown opportunity source type: $value'),
  };

  // ReliabilityLevel ("a".."f") and SourceVerificationStatus are spelled
  // identically on both sides -- .name round-trips directly.
  static String _levelToWire(ReliabilityLevel level) => level.name;

  static ReliabilityLevel _levelFromWire(String value) =>
      ReliabilityLevel.values.firstWhere(
        (level) => level.name == value,
        orElse: () =>
            throw LiveBackendException('Unknown reliability level: $value'),
      );

  static String _statusToWire(SourceVerificationStatus status) => status.name;

  static SourceVerificationStatus _statusFromWire(String value) =>
      SourceVerificationStatus.values.firstWhere(
        (status) => status.name == value,
        orElse: () => throw LiveBackendException(
          'Unknown source verification status: $value',
        ),
      );

  Future<dynamic> _get(
    String path, [
    Map<String, String> query = const {},
  ]) async {
    final headers = await _headers();
    final uri = Uri.parse(
      '$baseUrl$path',
    ).replace(queryParameters: query.isEmpty ? null : query);
    return _handle(() => _client.get(uri, headers: headers));
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.post(uri, headers: headers, body: jsonEncode(body)),
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
