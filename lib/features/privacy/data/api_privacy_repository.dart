import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/privacy_models.dart';
import '../domain/privacy_repository.dart';

/// Reads and writes real, per-user privacy data from the ScholarSphere
/// Python backend (scholarsphere_backend/).
///
/// This is the live replacement for [DemoPrivacyRepository]. [setMinorStatus]
/// is a documented no-op here: the Dart demo trusted a client-pushed
/// boolean, but the live backend computes minor status itself, freshly, at
/// consent-grant time from the caller's own real
/// [ApplicantProfile.dateOfBirth] (via [ApiApplicantProfileRepository]) -
/// never from a client-supplied flag a caller could misreport to bypass
/// restricted consents. [recordOrganizationAccess]/[recordIncident]/
/// [getIncidentsForAdministration] are staff-only server-side (no
/// self-service caller exists in this app today).
class ApiPrivacyRepository implements PrivacyRepository {
  ApiPrivacyRepository({
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
  Future<void> setMinorStatus(String userId, bool isMinor) async {}

  @override
  Future<List<ConsentRecord>> getConsents(String userId) async {
    final body = await _get('/privacy/consents');
    return (body as List<dynamic>)
        .map((item) => _toConsent(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> grantConsent({
    required String userId,
    required ConsentType type,
    required String policyVersion,
  }) async {
    try {
      await _post('/privacy/consents', {
        'type': _consentTypeToWire(type),
        'policy_version': policyVersion,
      });
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const PrivacyFailure(
          'This consent is restricted for minor accounts.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<void> withdrawConsent(String userId, ConsentType type) async {
    try {
      await _post(
        '/privacy/consents/${_consentTypeToWire(type)}/withdraw',
        const {},
      );
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const PrivacyFailure(
          'Required legal acceptance cannot be withdrawn while the account '
          'remains active. Submit an account-deletion request instead.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<PrivacyRequest> submitRequest({
    required String userId,
    required PrivacyRequestType type,
    String notes = '',
  }) async {
    final body = await _post('/privacy/requests', {
      'type': _requestTypeToWire(type),
      'notes': notes,
    });
    return _toRequest(body as Map<String, dynamic>);
  }

  @override
  Future<List<PrivacyRequest>> getRequests(String userId) async {
    final body = await _get('/privacy/requests');
    return (body as List<dynamic>)
        .map((item) => _toRequest(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<List<OrganizationAccessRecord>> getAccessHistory(String userId) async {
    final body = await _get('/privacy/access-history');
    return (body as List<dynamic>)
        .map((item) => _toAccessRecord(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> recordOrganizationAccess({
    required String userId,
    required String organizationId,
    required String organizationName,
    required Set<String> dataCategories,
  }) async {
    try {
      await _post('/privacy/access-history', {
        'user_id': userId,
        'organization_id': organizationId,
        'organization_name': organizationName,
        'data_categories': dataCategories.toList(),
      });
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const PrivacyFailure(
          'Third-party access requires explicit active user consent.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<void> recordIncident(PrivacyIncident incident) async {
    await _post('/privacy/incidents', {
      'summary': incident.summary,
      'affected_user_ids': incident.affectedUserIds.toList(),
    });
  }

  @override
  Future<List<PrivacyIncident>> getIncidentsForAdministration() async {
    final body = await _get('/privacy/incidents');
    return (body as List<dynamic>)
        .map((item) => _toIncident(item as Map<String, dynamic>))
        .toList();
  }

  ConsentRecord _toConsent(Map<String, dynamic> json) => ConsentRecord(
    userId: json['user_id'] as String,
    type: _consentTypeFromWire(json['type'] as String),
    policyVersion: json['policy_version'] as String,
    grantedAt: DateTime.parse(json['granted_at'] as String),
    withdrawnAt: _dateTime(json['withdrawn_at']),
  );

  PrivacyRequest _toRequest(Map<String, dynamic> json) => PrivacyRequest(
    id: json['id'] as String,
    userId: json['user_id'] as String,
    type: _requestTypeFromWire(json['type'] as String),
    status: _requestStatusFromWire(json['status'] as String),
    submittedAt: DateTime.parse(json['submitted_at'] as String),
    completedAt: _dateTime(json['completed_at']),
    notes: json['notes'] as String,
  );

  OrganizationAccessRecord _toAccessRecord(Map<String, dynamic> json) =>
      OrganizationAccessRecord(
        id: json['id'] as String,
        userId: json['user_id'] as String,
        organizationId: json['organization_id'] as String,
        organizationName: json['organization_name'] as String,
        dataCategories: (json['data_categories'] as List<dynamic>)
            .cast<String>()
            .toSet(),
        accessedAt: DateTime.parse(json['accessed_at'] as String),
        consentRecordType: _consentTypeFromWire(
          json['consent_record_type'] as String,
        ),
      );

  PrivacyIncident _toIncident(Map<String, dynamic> json) => PrivacyIncident(
    id: json['id'] as String,
    recordedAt: DateTime.parse(json['recorded_at'] as String),
    summary: json['summary'] as String,
    affectedUserIds: (json['affected_user_ids'] as List<dynamic>)
        .cast<String>()
        .toSet(),
    resolvedAt: _dateTime(json['resolved_at']),
  );

  static DateTime? _dateTime(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  // Keep these three maps in sync with app/schemas/privacy.py's wire maps.
  static String _consentTypeToWire(ConsentType type) => switch (type) {
    ConsentType.privacyPolicy => 'privacyPolicy',
    ConsentType.termsAndConditions => 'termsAndConditions',
    ConsentType.cookies => 'cookies',
    ConsentType.marketing => 'marketing',
    ConsentType.notifications => 'notifications',
    ConsentType.personalizedRecommendations => 'personalizedRecommendations',
    ConsentType.sensitiveData => 'sensitiveData',
    ConsentType.documentStorage => 'documentStorage',
    ConsentType.thirdPartySharing => 'thirdPartySharing',
  };

  static ConsentType _consentTypeFromWire(String value) => switch (value) {
    'privacyPolicy' => ConsentType.privacyPolicy,
    'termsAndConditions' => ConsentType.termsAndConditions,
    'cookies' => ConsentType.cookies,
    'marketing' => ConsentType.marketing,
    'notifications' => ConsentType.notifications,
    'personalizedRecommendations' => ConsentType.personalizedRecommendations,
    'sensitiveData' => ConsentType.sensitiveData,
    'documentStorage' => ConsentType.documentStorage,
    'thirdPartySharing' => ConsentType.thirdPartySharing,
    _ => throw LiveBackendException('Unknown consent type: $value'),
  };

  static String _requestTypeToWire(PrivacyRequestType type) => switch (type) {
    PrivacyRequestType.dataExport => 'dataExport',
    PrivacyRequestType.accountDeletion => 'accountDeletion',
    PrivacyRequestType.dataCorrection => 'dataCorrection',
    PrivacyRequestType.documentDeletion => 'documentDeletion',
  };

  static PrivacyRequestType _requestTypeFromWire(String value) =>
      switch (value) {
        'dataExport' => PrivacyRequestType.dataExport,
        'accountDeletion' => PrivacyRequestType.accountDeletion,
        'dataCorrection' => PrivacyRequestType.dataCorrection,
        'documentDeletion' => PrivacyRequestType.documentDeletion,
        _ => throw LiveBackendException('Unknown privacy request type: $value'),
      };

  static PrivacyRequestStatus _requestStatusFromWire(String value) =>
      switch (value) {
        'submitted' => PrivacyRequestStatus.submitted,
        'inReview' => PrivacyRequestStatus.inReview,
        'completed' => PrivacyRequestStatus.completed,
        'rejected' => PrivacyRequestStatus.rejected,
        'cancelled' => PrivacyRequestStatus.cancelled,
        _ => throw LiveBackendException(
          'Unknown privacy request status: $value',
        ),
      };

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
