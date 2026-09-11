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
/// notifications, calendar) and for [AdministrationAnalyticsService]'s
/// reporting (via [getAllForAdministration]). Provider self-submission
/// ([submit]/[getForProvider]) is a separate, unrelated backend feature
/// that doesn't exist yet, so it fails loudly rather than silently
/// returning demo data. Provider/moderation/verification screens are
/// unaffected - they still use [DemoOpportunityRepository], deliberately,
/// since the live backend's leaner data and single-reviewer model don't
/// match those screens' richer assumptions (see the engineering report).
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
  Future<List<Opportunity>> getAllForAdministration() async {
    const pageSize = 200;
    final opportunities = <Opportunity>[];
    var page = 1;
    var total = 0;
    do {
      final body =
          await _get('/external-opportunities/opportunities', {
                'page': '$page',
                'page_size': '$pageSize',
              })
              as Map<String, dynamic>;
      final items = body['items'] as List<dynamic>;
      total = body['total'] as int? ?? items.length;
      opportunities.addAll(
        items
            .map(
              (item) => _toOpportunity(
                item as Map<String, dynamic>,
                verificationStatus: _verificationStatusFromWire(
                  item['verification_status'] as String,
                ),
              ),
            )
            .whereType<Opportunity>(),
      );
      if (items.isEmpty) break;
      page += 1;
    } while ((page - 1) * pageSize < total);
    return opportunities;
  }

  // The live backend's VerificationStatus (pending, verified, rejected,
  // suspicious, expired, archived, reverification_required,
  // source_unavailable) doesn't map 1:1 onto Opportunity's (which has
  // verificationExpired/incomplete instead of those last two) - the two
  // reasoned equivalents used here: a record whose prior verification
  // lapsed and needs a fresh look ("reverification_required") is closest
  // to [VerificationStatus.verificationExpired]; one whose source can no
  // longer be reached to confirm anything ("source_unavailable") is
  // closest to [VerificationStatus.incomplete].
  static VerificationStatus _verificationStatusFromWire(String value) =>
      switch (value) {
        'pending' => VerificationStatus.pending,
        'verified' => VerificationStatus.verified,
        'rejected' => VerificationStatus.rejected,
        'suspicious' => VerificationStatus.suspicious,
        'expired' => VerificationStatus.expired,
        'archived' => VerificationStatus.archived,
        'reverification_required' => VerificationStatus.verificationExpired,
        'source_unavailable' => VerificationStatus.incomplete,
        _ => throw LiveBackendException('Unknown verification status: $value'),
      };

  Opportunity? _toOpportunity(
    Map<String, dynamic> json, {
    VerificationStatus verificationStatus = VerificationStatus.verified,
  }) {
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
      funding: _mapFundingType(json['funding_type'] as String?),
      deadline: deadline,
      applicationOpenDate: opening,
      verificationStatus: verificationStatus,
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
    if (rawType.contains('fellowship')) return OpportunityType.fellowship;
    if (rawType.contains('scholarship')) return OpportunityType.scholarship;
    if (rawType == 'job') return OpportunityType.job;
    return OpportunityType.grant;
  }

  static DateTime? _date(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  /// The backend's real `funding_type` values are `fully_funded` or
  /// `partial_funding` when a source's coverage was actually researched
  /// (see e.g. app/services/national_scholarship_programs.py) - both
  /// mapped honestly here. Most bulk-imported records (Grants.gov,
  /// USAJOBS, ReliefWeb...) never set this field at all, and a `grant`
  /// value only reflects the record's opportunity type, not its funding
  /// coverage - neither tells us whether the award is full or partial,
  /// so both fall back to [FundingType.partiallyFunded] rather than
  /// claiming "fully funded" without evidence.
  static FundingType _mapFundingType(String? raw) => switch (raw) {
    'fully_funded' => FundingType.fullyFunded,
    'partial_funding' => FundingType.partiallyFunded,
    _ => FundingType.partiallyFunded,
  };

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
