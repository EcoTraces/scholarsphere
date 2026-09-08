import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/legal_compliance.dart';
import '../domain/legal_compliance_repository.dart';

/// Reads and writes real legal-policy, acceptance, and compliance data
/// from the ScholarSphere Python backend. Live replacement for
/// [DemoLegalComplianceRepository].
///
/// [accept]'s `userId` is taken from the caller's own verified auth
/// token server-side, never trusted from the client, so a caller can
/// only ever record their own policy acceptance.
class ApiLegalComplianceRepository implements LegalComplianceRepository {
  ApiLegalComplianceRepository({
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
  Future<LegalPolicy> publish(LegalPolicy policy) async {
    try {
      final body = await _post('/legal/policies', {
        'id': policy.id,
        'type': _policyTypeToWire(policy.type),
        'version': policy.version,
        'title': policy.title,
        'content': policy.content,
        'effective_at': policy.effectiveAt.toUtc().toIso8601String(),
        'requires_acceptance': policy.requiresAcceptance,
        'material_change': policy.materialChange,
      });
      return _toPolicy(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw StateError('This policy version already exists.');
      }
      rethrow;
    }
  }

  @override
  Future<LegalPolicy?> current(LegalPolicyType type) async {
    // Deliberately the one call in this repository that works signed out
    // (matches the backend route, which is public for the same reason):
    // a visitor must be able to read Terms & Conditions / Privacy Policy
    // from the public footer or the registration form's consent
    // checkboxes before ever creating an account.
    final body = await _get(
      '/legal/policies/${_policyTypeToWire(type)}/current',
      requireAuth: false,
    );
    if (body == null) return null;
    return _toPolicy(body as Map<String, dynamic>);
  }

  @override
  Future<List<LegalPolicy>> versions(LegalPolicyType type) async {
    final body = await _get(
      '/legal/policies/${_policyTypeToWire(type)}/versions',
    );
    return (body as List<dynamic>)
        .map((item) => _toPolicy(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> accept(PolicyAcceptance acceptance) async {
    try {
      await _post('/legal/acceptances', {
        'policy_id': acceptance.policyId,
        'policy_version': acceptance.policyVersion,
        'ip_address': acceptance.ipAddress,
      });
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw StateError('Policy was not found.');
      }
      if (error.statusCode == 409) {
        throw StateError('Only the current policy version can be accepted.');
      }
      rethrow;
    }
  }

  @override
  Future<bool> hasAcceptedCurrent(String userId, LegalPolicyType type) async {
    final body = await _get(
      '/legal/policies/${_policyTypeToWire(type)}/accepted',
    );
    return body as bool;
  }

  @override
  Future<List<String>> pendingPolicyNotifications(String userId) async {
    final body = await _get('/legal/pending-notifications');
    return (body as List<dynamic>).cast<String>();
  }

  @override
  Future<LegalRequest> submitLegalRequest(LegalRequest request) async {
    try {
      final body = await _post('/legal/requests', {
        'id': request.id,
        'type': _requestTypeToWire(request.type),
        'requester': request.requester,
        'subject_entity_id': request.subjectEntityId,
        'description': request.description,
        'evidence_locations': request.evidenceLocations,
      });
      return _toRequest(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 422) {
        throw StateError('A legal request description is required.');
      }
      rethrow;
    }
  }

  @override
  Future<List<LegalRequest>> legalRequests() async {
    final body = await _get('/legal/requests');
    return (body as List<dynamic>)
        .map((item) => _toRequest(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> saveComplianceRecord(ComplianceRecord record) async {
    await _put('/legal/compliance/${record.id}', {
      'framework': record.framework,
      'obligation': record.obligation,
      'status': record.status,
      'owner': record.owner,
      'review_due_at': record.reviewDueAt.toUtc().toIso8601String(),
      'evidence_locations': record.evidenceLocations,
    });
  }

  @override
  Future<List<ComplianceRecord>> complianceRecords() async {
    final body = await _get('/legal/compliance');
    return (body as List<dynamic>)
        .map((item) => _toComplianceRecord(item as Map<String, dynamic>))
        .toList();
  }

  LegalPolicy _toPolicy(Map<String, dynamic> json) => LegalPolicy(
    id: json['id'] as String,
    type: _policyTypeFromWire(json['type'] as String),
    version: json['version'] as String,
    title: json['title'] as String,
    content: json['content'] as String,
    effectiveAt: DateTime.parse(json['effective_at'] as String),
    publishedAt: DateTime.parse(json['published_at'] as String),
    requiresAcceptance: json['requires_acceptance'] as bool,
    materialChange: json['material_change'] as bool,
    publishedBy: json['published_by'] as String,
  );

  LegalRequest _toRequest(Map<String, dynamic> json) => LegalRequest(
    id: json['id'] as String,
    type: _requestTypeFromWire(json['type'] as String),
    requester: json['requester'] as String,
    subjectEntityId: json['subject_entity_id'] as String,
    description: json['description'] as String,
    evidenceLocations: (json['evidence_locations'] as List<dynamic>)
        .cast<String>(),
    status: _requestStatusFromWire(json['status'] as String),
    createdAt: DateTime.parse(json['created_at'] as String),
    history: (json['history'] as List<dynamic>).cast<String>(),
  );

  ComplianceRecord _toComplianceRecord(Map<String, dynamic> json) =>
      ComplianceRecord(
        id: json['id'] as String,
        framework: json['framework'] as String,
        obligation: json['obligation'] as String,
        status: json['status'] as String,
        owner: json['owner'] as String,
        reviewDueAt: DateTime.parse(json['review_due_at'] as String),
        evidenceLocations: (json['evidence_locations'] as List<dynamic>)
            .cast<String>(),
      );

  // Keep in sync with app/schemas/legal_compliance.py's wire maps.
  static String _policyTypeToWire(LegalPolicyType type) => switch (type) {
    LegalPolicyType.termsAndConditions => 'termsAndConditions',
    LegalPolicyType.privacyPolicy => 'privacyPolicy',
    LegalPolicyType.cookiePolicy => 'cookiePolicy',
    LegalPolicyType.acceptableUse => 'acceptableUse',
    LegalPolicyType.providerAgreement => 'providerAgreement',
    LegalPolicyType.contentPublishing => 'contentPublishing',
    LegalPolicyType.verificationDisclaimer => 'verificationDisclaimer',
    LegalPolicyType.fundingDisclaimer => 'fundingDisclaimer',
    LegalPolicyType.copyrightPolicy => 'copyrightPolicy',
    LegalPolicyType.dataProcessingAgreement => 'dataProcessingAgreement',
  };

  static LegalPolicyType _policyTypeFromWire(String value) => switch (value) {
    'termsAndConditions' => LegalPolicyType.termsAndConditions,
    'privacyPolicy' => LegalPolicyType.privacyPolicy,
    'cookiePolicy' => LegalPolicyType.cookiePolicy,
    'acceptableUse' => LegalPolicyType.acceptableUse,
    'providerAgreement' => LegalPolicyType.providerAgreement,
    'contentPublishing' => LegalPolicyType.contentPublishing,
    'verificationDisclaimer' => LegalPolicyType.verificationDisclaimer,
    'fundingDisclaimer' => LegalPolicyType.fundingDisclaimer,
    'copyrightPolicy' => LegalPolicyType.copyrightPolicy,
    'dataProcessingAgreement' => LegalPolicyType.dataProcessingAgreement,
    _ => throw LiveBackendException('Unknown legal policy type: $value'),
  };

  static String _requestTypeToWire(LegalRequestType type) => switch (type) {
    LegalRequestType.takedown => 'takedown',
    LegalRequestType.complaint => 'complaint',
    LegalRequestType.regulator => 'regulator',
    LegalRequestType.courtOrder => 'courtOrder',
    LegalRequestType.dataProtection => 'dataProtection',
  };

  static LegalRequestType _requestTypeFromWire(String value) => switch (value) {
    'takedown' => LegalRequestType.takedown,
    'complaint' => LegalRequestType.complaint,
    'regulator' => LegalRequestType.regulator,
    'courtOrder' => LegalRequestType.courtOrder,
    'dataProtection' => LegalRequestType.dataProtection,
    _ => throw LiveBackendException('Unknown legal request type: $value'),
  };

  static LegalRequestStatus _requestStatusFromWire(String value) =>
      switch (value) {
        'submitted' => LegalRequestStatus.submitted,
        'validated' => LegalRequestStatus.validated,
        'inReview' => LegalRequestStatus.inReview,
        'actioned' => LegalRequestStatus.actioned,
        'rejected' => LegalRequestStatus.rejected,
        'closed' => LegalRequestStatus.closed,
        _ => throw LiveBackendException('Unknown legal request status: $value'),
      };

  Future<dynamic> _get(String path, {bool requireAuth = true}) async {
    final headers = requireAuth ? await _headers() : await _optionalHeaders();
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

  /// Same as [_headers], but for the one endpoint that also serves signed
  /// out visitors: sends a bearer token when one is available, omits it
  /// otherwise, rather than throwing.
  Future<Map<String, String>> _optionalHeaders() async {
    final user = _auth.currentUser;
    final headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
    if (user != null) {
      headers['Authorization'] = 'Bearer ${await user.getIdToken()}';
    }
    return headers;
  }

  void dispose() => _client.close();
}
