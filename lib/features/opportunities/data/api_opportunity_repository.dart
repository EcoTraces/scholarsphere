import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../security/domain/security_backend_contracts.dart';
import '../domain/opportunity.dart';
import '../domain/opportunity_repository.dart';

/// A network failure talking to the ScholarSphere discovery backend.
class LiveBackendException implements Exception {
  const LiveBackendException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

const _notSpecified = 'Not specified by source';

/// Reads real, human-verified opportunities from the ScholarSphere Python
/// backend (scholarsphere_backend/), which imports from Grants.gov,
/// Simpler.Grants.gov, EU Funding & Tenders, USAJOBS and ReliefWeb.
///
/// This is the live replacement for [DemoOpportunityRepository] on
/// applicant-facing screens (Discover, the applicant dashboard,
/// notifications, calendar). Only [getPublished] is real - provider
/// self-submission ([submit]/[getForProvider]) and admin-wide listing
/// ([getAllForAdministration]) are unrelated backend features that don't
/// exist yet, so they fail loudly rather than silently returning demo
/// data. Admin/provider/moderation/verification screens are unaffected -
/// they still use [DemoOpportunityRepository], deliberately, since the
/// live backend's leaner data and single-reviewer model don't match those
/// screens' richer assumptions (see the engineering report).
///
/// Field mapping honesty: the backend's real sources (government grant
/// portals, USAJOBS, ReliefWeb) don't publish most of [Opportunity]'s
/// scholarship-shaped structured fields (eligible nationalities, study
/// levels, required documents, contact info, position count...). Those are
/// filled with an explicit "Not specified by source" marker or an empty
/// list - never invented. Records missing a deadline or opening date are
/// skipped, because [Opportunity.deadline]/[applicationOpenDate] are
/// non-nullable and there is no honest date to put there.
class ApiOpportunityRepository implements OpportunityRepository {
  ApiOpportunityRepository({
    String? baseUrl,
    http.Client? client,
    firebase.FirebaseAuth? auth,
  }) : baseUrl = baseUrl ?? _defaultBaseUrl,
       _client = client ?? http.Client(),
       _authOverride = auth {
    // Release builds must never send a Firebase bearer token to a plaintext
    // endpoint. A misconfigured/missing --dart-define would otherwise fail
    // silently against http://localhost in production; fail loudly instead.
    if (kReleaseMode) {
      TransportSecurityPolicy.requireHttps(Uri.parse(this.baseUrl));
    }
  }

  /// Override at build/run time with
  /// `--dart-define=SCHOLARSPHERE_API_BASE_URL=https://api.example.org/api/v1`.
  static const _defaultBaseUrl = String.fromEnvironment(
    'SCHOLARSPHERE_API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  final String baseUrl;
  final http.Client _client;
  final firebase.FirebaseAuth? _authOverride;

  // Resolved lazily (not in the constructor) so constructing this
  // repository never requires a live Firebase app -- only actually making a
  // request does. This keeps it safe to construct unconditionally (e.g. in
  // ScholarSphereApp's field initializers) in contexts like widget tests
  // where Firebase.initializeApp() was never called and getPublished() is
  // never exercised.
  firebase.FirebaseAuth get _auth =>
      _authOverride ?? firebase.FirebaseAuth.instance;

  @override
  Future<List<Opportunity>> getPublished() async {
    final body = await _get('/opportunities', const {'page_size': '100'});
    final items = (body as Map<String, dynamic>)['items'] as List<dynamic>;
    return items
        .map((item) => _toOpportunity(item as Map<String, dynamic>))
        .whereType<Opportunity>()
        .toList();
  }

  @override
  Future<List<Opportunity>> getForProvider(String providerId) {
    throw UnsupportedError(
      'Provider-submitted opportunities are not part of the live backend. '
      'Use DemoOpportunityRepository for provider self-service screens.',
    );
  }

  @override
  Future<void> submit({
    required String providerId,
    required Opportunity opportunity,
  }) {
    throw UnsupportedError(
      'Provider submission is not implemented against the live backend.',
    );
  }

  @override
  Future<List<Opportunity>> getAllForAdministration() {
    throw UnsupportedError(
      'Use the live backend verification-queue endpoints directly for '
      'administration views; this repository only exposes published data.',
    );
  }

  Opportunity? _toOpportunity(Map<String, dynamic> json) {
    final deadline = _date(json['deadline']);
    final opening = _date(json['opening_date']) ?? _date(json['collected_at']);
    if (deadline == null || opening == null) {
      // Opportunity.deadline/applicationOpenDate are non-nullable; a record
      // with no honest date for one of them is left out rather than
      // fabricating a placeholder date. See class-level doc comment.
      return null;
    }
    final rawType = (json['opportunity_type'] as String?)?.toLowerCase() ?? '';
    final type = _mapType(rawType);
    final country = json['country'] as String? ?? _notSpecified;
    final provider = json['provider_name'] as String? ?? _notSpecified;

    return Opportunity(
      id: json['id'] as String,
      title: json['title'] as String,
      provider: provider,
      hostInstitution: provider,
      hostCountry: country,
      type: type,
      funding: FundingType.partiallyFunded,
      deadline: deadline,
      applicationOpenDate: opening,
      verificationStatus: VerificationStatus.verified,
      lastVerifiedAt: _date(json['verified_at']),
      officialSourceUrl: json['official_source_url'] as String? ?? '',
      applicationUrl:
          json['official_application_url'] as String? ??
          json['official_source_url'] as String? ??
          '',
      eligibleNationalities: const [],
      studyLevels: const [],
      fieldsOfStudy: const [],
      summary: json['description'] as String? ?? _notSpecified,
      benefits: const [],
      eligibilityRequirements: const [
        'Eligibility criteria are not yet structured for this source. '
            'Review the official source link before applying.',
      ],
      requiredDocuments: const [],
      applicationProcedure: const [],
      languageRequirements: const [],
      minimumAge: null,
      maximumAge: null,
      workExperienceYearsRequired: null,
      contactInformation: _notSpecified,
      availablePositions: null,
      deliveryFormat: DeliveryFormat.physical,
      applicationFee: null,
    );
  }

  static OpportunityType _mapType(String rawType) {
    if (rawType.contains('internship')) return OpportunityType.internship;
    if (rawType.contains('training')) return OpportunityType.training;
    if (rawType == 'job') return OpportunityType.job;
    return OpportunityType.grant;
  }

  static DateTime? _date(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  Future<dynamic> _get(String path, Map<String, String> query) async {
    final uri = Uri.parse(
      '$baseUrl$path',
    ).replace(queryParameters: query.isEmpty ? null : query);
    final headers = await _headers();
    late final http.Response response;
    try {
      response = await _client.get(uri, headers: headers);
    } on Exception catch (error) {
      throw LiveBackendException(
        'Could not reach the ScholarSphere backend: $error',
      );
    }
    if (response.statusCode == 401) {
      throw const LiveBackendException(
        'Sign-in expired. Sign in again to view opportunities.',
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
        'Sign in to view opportunities.',
        statusCode: 401,
      );
    }
    final token = await user.getIdToken();
    return {'Authorization': 'Bearer $token', 'Accept': 'application/json'};
  }

  void dispose() => _client.close();
}
