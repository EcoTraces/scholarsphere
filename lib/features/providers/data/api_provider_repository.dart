import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/provider_profile.dart';
import '../domain/provider_repository.dart';

/// Reads and writes real provider-organization records from the
/// ScholarSphere Python backend (scholarsphere_backend/).
///
/// This is the live replacement for [DemoProviderRepository]. The backend,
/// not this client, decides ownership: registration, appeal, and
/// administrator-management requests are scoped to the caller's own
/// Firebase UID from the bearer token, never a client-supplied parameter.
/// Business-rule rejections (duplicate domain, incomplete review checklist,
/// appeal from a non-appealable status, adding an admin to an unverified
/// provider) surface as [ProviderFailure], matching the documented
/// interface contract.
class ApiProviderRepository implements ProviderRepository {
  ApiProviderRepository({
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
  Future<ProviderProfile?> getForUser(String userId) async {
    try {
      final body = await _get('/providers/me');
      return _toProfile(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<List<ProviderProfile>> getReviewQueue() async {
    final body = await _get('/providers/review-queue');
    final items = body as List<dynamic>;
    return items
        .map((item) => _toProfile(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<ProviderProfile> register(ProviderProfile profile) async {
    final body = await _post('/providers', {
      'organization_name': profile.organizationName,
      'organization_type': profile.organizationType,
      'registration_number': profile.registrationNumber,
      'country': profile.country,
      'official_website': profile.officialWebsite,
      'official_email_domain': profile.officialEmailDomain,
      'physical_address': profile.physicalAddress,
      'contact_person': profile.contactPerson,
      'contact_phone': profile.contactPhone,
      'supporting_documents': profile.supportingDocuments,
      'social_media_links': profile.socialMediaLinks,
    }, businessErrorContext: 'register the organization');
    return _toProfile(body as Map<String, dynamic>);
  }

  @override
  Future<ProviderProfile> review({
    required String providerId,
    required String officerId,
    required ProviderStatus decision,
    required ProviderReviewChecklist checklist,
    String? note,
  }) async {
    final body = await _post('/providers/$providerId/review', {
      'decision': _statusToWire(decision),
      'official_email_verified': checklist.officialEmailVerified,
      'domain_verified': checklist.domainVerified,
      'contact_verified': checklist.contactVerified,
      'documents_verified': checklist.documentsVerified,
      'impersonation_check_passed': checklist.impersonationCheckPassed,
      'note': note,
    }, businessErrorContext: 'review the organization');
    return _toProfile(body as Map<String, dynamic>);
  }

  @override
  Future<ProviderProfile> suspend(String providerId, String reason) async {
    final body = await _post('/providers/$providerId/suspend', {
      'reason': reason,
    }, businessErrorContext: 'suspend the organization');
    return _toProfile(body as Map<String, dynamic>);
  }

  @override
  Future<ProviderProfile> appeal(String providerId, String reason) async {
    final body = await _post('/providers/$providerId/appeal', {
      'reason': reason,
    }, businessErrorContext: 'submit the appeal');
    return _toProfile(body as Map<String, dynamic>);
  }

  @override
  Future<ProviderProfile> addAdministrator(
    String providerId,
    ProviderAdministrator administrator,
  ) async {
    final body = await _post('/providers/$providerId/administrators', {
      'user_id': administrator.userId,
      'email': administrator.email,
      'permissions': administrator.permissions.map(_permissionToWire).toList(),
    }, businessErrorContext: 'add the administrator');
    return _toProfile(body as Map<String, dynamic>);
  }

  @override
  Future<bool> canPublish(String userId) async {
    final body =
        await _get('/providers/me/can-publish') as Map<String, dynamic>;
    return body['can_publish'] as bool;
  }

  ProviderProfile _toProfile(Map<String, dynamic> json) => ProviderProfile(
    id: json['id'] as String,
    ownerUserId: json['user_id'] as String,
    organizationName: json['organization_name'] as String,
    organizationType: json['organization_type'] as String,
    registrationNumber: json['registration_number'] as String,
    country: json['country'] as String,
    officialWebsite: json['official_website'] as String,
    officialEmailDomain: json['official_email_domain'] as String,
    physicalAddress: json['physical_address'] as String,
    contactPerson: json['contact_person'] as String,
    contactPhone: json['contact_phone'] as String,
    supportingDocuments: (json['supporting_documents'] as List<dynamic>)
        .cast<String>(),
    socialMediaLinks: (json['social_media_links'] as List<dynamic>)
        .cast<String>(),
    status: _statusFromWire(json['status'] as String),
    riskScore: json['risk_score'] as int,
    permissions: (json['permissions'] as List<dynamic>)
        .map((value) => _permissionFromWire(value as String))
        .toSet(),
    administrators: (json['administrators'] as List<dynamic>)
        .map((item) => _toAdministrator(item as Map<String, dynamic>))
        .toList(),
    activityHistory: (json['activity_history'] as List<dynamic>)
        .map((item) => _toActivity(item as Map<String, dynamic>))
        .toList(),
    appeals: (json['appeals'] as List<dynamic>)
        .map((item) => _toAppeal(item as Map<String, dynamic>))
        .toList(),
    verificationDate: _date(json['verification_date']),
    verifiedBy: json['verified_by'] as String?,
    reverificationDate: _date(json['reverification_date']),
    reviewNote: json['review_note'] as String?,
  );

  ProviderAdministrator _toAdministrator(Map<String, dynamic> json) =>
      ProviderAdministrator(
        userId: json['user_id'] as String,
        email: json['email'] as String,
        permissions: (json['permissions'] as List<dynamic>)
            .map((value) => _permissionFromWire(value as String))
            .toSet(),
      );

  ProviderActivity _toActivity(Map<String, dynamic> json) => ProviderActivity(
    action: json['action'] as String,
    actorId: json['actor_id'] as String,
    occurredAt: DateTime.parse(json['occurred_at'] as String),
  );

  ProviderAppeal _toAppeal(Map<String, dynamic> json) => ProviderAppeal(
    reason: json['reason'] as String,
    submittedAt: DateTime.parse(json['submitted_at'] as String),
    status: json['status'] as String,
  );

  // Keep in sync with `_STATUS_WIRE_TO_MODEL` in
  // scholarsphere_backend/app/schemas/provider.py.
  static ProviderStatus _statusFromWire(String value) => switch (value) {
    'draft' => ProviderStatus.draft,
    'pendingReview' => ProviderStatus.pendingReview,
    'additionalInformationRequired' =>
      ProviderStatus.additionalInformationRequired,
    'verified' => ProviderStatus.verified,
    'rejected' => ProviderStatus.rejected,
    'suspended' => ProviderStatus.suspended,
    'verificationExpired' => ProviderStatus.verificationExpired,
    'archived' => ProviderStatus.archived,
    _ => throw LiveBackendException('Unknown provider status: $value'),
  };

  static String _statusToWire(ProviderStatus status) => switch (status) {
    ProviderStatus.draft => 'draft',
    ProviderStatus.pendingReview => 'pendingReview',
    ProviderStatus.additionalInformationRequired =>
      'additionalInformationRequired',
    ProviderStatus.verified => 'verified',
    ProviderStatus.rejected => 'rejected',
    ProviderStatus.suspended => 'suspended',
    ProviderStatus.verificationExpired => 'verificationExpired',
    ProviderStatus.archived => 'archived',
  };

  // Keep in sync with `_PERMISSION_WIRE_TO_MODEL` in
  // scholarsphere_backend/app/schemas/provider.py.
  static ProviderPermission _permissionFromWire(String value) =>
      switch (value) {
        'manageOrganization' => ProviderPermission.manageOrganization,
        'publishOpportunities' => ProviderPermission.publishOpportunities,
        'manageAdmins' => ProviderPermission.manageAdmins,
        _ => throw LiveBackendException('Unknown provider permission: $value'),
      };

  static String _permissionToWire(ProviderPermission permission) =>
      switch (permission) {
        ProviderPermission.manageOrganization => 'manageOrganization',
        ProviderPermission.publishOpportunities => 'publishOpportunities',
        ProviderPermission.manageAdmins => 'manageAdmins',
      };

  static DateTime? _date(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  Future<dynamic> _get(String path) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(() => _client.get(uri, headers: headers));
  }

  Future<dynamic> _post(
    String path,
    Map<String, dynamic> body, {
    String? businessErrorContext,
  }) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    try {
      return await _handle(
        () => _client.post(uri, headers: headers, body: jsonEncode(body)),
      );
    } on LiveBackendException catch (error) {
      if (businessErrorContext != null && error.statusCode == 409) {
        throw ProviderFailure(
          'Could not $businessErrorContext: the request violates a '
          'verification rule.',
        );
      }
      rethrow;
    }
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
    return jsonDecode(response.body);
  }

  Future<Map<String, String>> _headers() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const LiveBackendException(
        'Sign in to manage your organization.',
        statusCode: 401,
      );
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
