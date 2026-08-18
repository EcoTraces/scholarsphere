import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../security/domain/security_backend_contracts.dart';
import '../domain/opportunity.dart';
import '../domain/opportunity_repository.dart';
import 'api_opportunity_repository.dart' show LiveBackendException;

const _notSpecified = 'Not specified by source';

/// Reads and writes real, provider-submitted opportunities from the
/// ScholarSphere Python backend's provider-opportunity pipeline
/// (`/provider-opportunities/*`) - a separate table and verify/publish
/// workflow from the Grants.gov-family pipeline [ApiOpportunityRepository]
/// serves.
///
/// This is the live replacement for [DemoOpportunityRepository] on the
/// provider-facing screens ([ProviderOpportunityScreen],
/// [OpportunitySubmissionScreen]) only - [getPublished] throws
/// [UnsupportedError], mirroring [ApiOpportunityRepository]'s own
/// unsupported-method pattern for the opposite slice of the interface.
/// Provider-submitted opportunities are never mixed into the applicant-
/// facing public listing; that stays exclusively the Grants.gov-family
/// pipeline (see the Provider implementation plan for why).
///
/// The `providerId` parameters accepted by [getForProvider]/[submit] are
/// part of the [OpportunityRepository] interface contract but are not
/// trusted as-is: the backend only knows the caller's own provider
/// organization (via `/providers/me`, resolved from the caller's Firebase
/// UID), so that is what is actually used - matching how
/// [ApiApplicationRepository] ignores a client-supplied userId in favor of
/// the bearer token's identity.
class ApiProviderOpportunityRepository implements OpportunityRepository {
  ApiProviderOpportunityRepository({
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
  Future<List<Opportunity>> getPublished() {
    throw UnsupportedError(
      'The Grants.gov-family public listing is served by '
      'ApiOpportunityRepository, not this provider-opportunity repository.',
    );
  }

  @override
  Future<List<Opportunity>> getForProvider(String providerId) async {
    final myProviderId = await _resolveMyProviderId();
    final body = await _get('/provider-opportunities/mine/$myProviderId');
    final items = body as List<dynamic>;
    return items
        .map((item) => _toOpportunity(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> submit({
    required String providerId,
    required Opportunity opportunity,
  }) async {
    final myProviderId = await _resolveMyProviderId();
    await _post('/provider-opportunities', {
      'provider_id': myProviderId,
      'title': opportunity.title,
      'host_institution': opportunity.hostInstitution,
      'host_country': opportunity.hostCountry,
      'opportunity_type': _typeToWire(opportunity.type),
      'funding_type': _fundingToWire(opportunity.funding),
      'delivery_format': _deliveryToWire(opportunity.deliveryFormat),
      'deadline': _dateString(opportunity.deadline),
      'application_open_date': _dateString(opportunity.applicationOpenDate),
      'official_source_url': opportunity.officialSourceUrl,
      'application_url': opportunity.applicationUrl,
      'eligible_nationalities': opportunity.eligibleNationalities,
      'study_levels': opportunity.studyLevels,
      'fields_of_study': opportunity.fieldsOfStudy,
      'summary': opportunity.summary,
      'benefits': opportunity.benefits,
      'eligibility_requirements': opportunity.eligibilityRequirements,
      'required_documents': opportunity.requiredDocuments,
      'application_procedure': opportunity.applicationProcedure,
      'language_requirements': opportunity.languageRequirements,
      'minimum_age': opportunity.minimumAge,
      'maximum_age': opportunity.maximumAge,
      'work_experience_years_required':
          opportunity.workExperienceYearsRequired,
      'contact_information': opportunity.contactInformation,
      'available_positions': opportunity.availablePositions,
      'application_fee': opportunity.applicationFee,
    });
  }

  @override
  Future<List<Opportunity>> getAllForAdministration() async {
    final opportunities = <Opportunity>[];
    var page = 1;
    const pageSize = 100;
    while (true) {
      final body =
          await _get(
                '/provider-opportunities/admin',
                query: {'page': '$page', 'page_size': '$pageSize'},
              )
              as Map<String, dynamic>;
      final items = (body['items'] as List<dynamic>)
          .map((item) => _toOpportunity(item as Map<String, dynamic>))
          .toList();
      opportunities.addAll(items);
      if (items.length < pageSize) break;
      page += 1;
    }
    return opportunities;
  }

  Future<String> _resolveMyProviderId() async {
    try {
      final body = await _get('/providers/me') as Map<String, dynamic>;
      return body['id'] as String;
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const LiveBackendException(
          'No organization is registered for this account.',
        );
      }
      rethrow;
    }
  }

  Opportunity _toOpportunity(Map<String, dynamic> json) => Opportunity(
    id: json['id'] as String,
    title: json['title'] as String,
    provider: json['provider_name'] as String,
    hostInstitution: json['host_institution'] as String,
    hostCountry: json['host_country'] as String,
    type: _typeFromWire(json['opportunity_type'] as String),
    funding: _fundingFromWire(json['funding_type'] as String),
    deadline: DateTime.parse(json['deadline'] as String),
    applicationOpenDate: DateTime.parse(
      json['application_open_date'] as String,
    ),
    verificationStatus: _verificationFromWire(
      json['verification_status'] as String,
    ),
    lastVerifiedAt: _date(json['last_verified_at']),
    officialSourceUrl: json['official_source_url'] as String,
    applicationUrl: json['application_url'] as String,
    eligibleNationalities: (json['eligible_nationalities'] as List<dynamic>)
        .cast<String>(),
    studyLevels: (json['study_levels'] as List<dynamic>).cast<String>(),
    fieldsOfStudy: (json['fields_of_study'] as List<dynamic>).cast<String>(),
    summary: json['summary'] as String,
    benefits: (json['benefits'] as List<dynamic>).cast<String>(),
    eligibilityRequirements:
        (json['eligibility_requirements'] as List<dynamic>).cast<String>(),
    requiredDocuments: (json['required_documents'] as List<dynamic>)
        .cast<String>(),
    applicationProcedure: (json['application_procedure'] as List<dynamic>)
        .cast<String>(),
    languageRequirements: (json['language_requirements'] as List<dynamic>)
        .cast<String>(),
    minimumAge: json['minimum_age'] as int?,
    maximumAge: json['maximum_age'] as int?,
    workExperienceYearsRequired:
        (json['work_experience_years_required'] as num?)?.toDouble(),
    contactInformation: json['contact_information'] as String? ?? _notSpecified,
    availablePositions: json['available_positions'] as int?,
    deliveryFormat: _deliveryFromWire(json['delivery_format'] as String),
    applicationFee: (json['application_fee'] as num?)?.toDouble(),
  );

  // Keep in sync with `_TYPE_WIRE_TO_MODEL` in
  // scholarsphere_backend/app/schemas/provider_opportunity.py.
  static OpportunityType _typeFromWire(String value) => switch (value) {
    'scholarship' => OpportunityType.scholarship,
    'fellowship' => OpportunityType.fellowship,
    'internship' => OpportunityType.internship,
    'conference' => OpportunityType.conference,
    'summit' => OpportunityType.summit,
    'webinar' => OpportunityType.webinar,
    'exchangeProgram' => OpportunityType.exchangeProgram,
    'researchGrant' => OpportunityType.researchGrant,
    'competition' => OpportunityType.competition,
    'training' => OpportunityType.training,
    'volunteering' => OpportunityType.volunteering,
    'youthProgram' => OpportunityType.youthProgram,
    'onlineCourse' => OpportunityType.onlineCourse,
    'fundedEvent' => OpportunityType.fundedEvent,
    'grant' => OpportunityType.grant,
    'job' => OpportunityType.job,
    _ => throw LiveBackendException('Unknown opportunity type: $value'),
  };

  static String _typeToWire(OpportunityType type) => switch (type) {
    OpportunityType.scholarship => 'scholarship',
    OpportunityType.fellowship => 'fellowship',
    OpportunityType.internship => 'internship',
    OpportunityType.conference => 'conference',
    OpportunityType.summit => 'summit',
    OpportunityType.webinar => 'webinar',
    OpportunityType.exchangeProgram => 'exchangeProgram',
    OpportunityType.researchGrant => 'researchGrant',
    OpportunityType.competition => 'competition',
    OpportunityType.training => 'training',
    OpportunityType.volunteering => 'volunteering',
    OpportunityType.youthProgram => 'youthProgram',
    OpportunityType.onlineCourse => 'onlineCourse',
    OpportunityType.fundedEvent => 'fundedEvent',
    OpportunityType.grant => 'grant',
    OpportunityType.job => 'job',
  };

  // Keep in sync with `_FUNDING_WIRE_TO_MODEL` in
  // scholarsphere_backend/app/schemas/provider_opportunity.py.
  static FundingType _fundingFromWire(String value) => switch (value) {
    'fullyFunded' => FundingType.fullyFunded,
    'partiallyFunded' => FundingType.partiallyFunded,
    'selfFunded' => FundingType.selfFunded,
    _ => throw LiveBackendException('Unknown funding type: $value'),
  };

  static String _fundingToWire(FundingType funding) => switch (funding) {
    FundingType.fullyFunded => 'fullyFunded',
    FundingType.partiallyFunded => 'partiallyFunded',
    FundingType.selfFunded => 'selfFunded',
  };

  // Keep in sync with `_DELIVERY_WIRE_TO_MODEL` in
  // scholarsphere_backend/app/schemas/provider_opportunity.py.
  static DeliveryFormat _deliveryFromWire(String value) => switch (value) {
    'online' => DeliveryFormat.online,
    'physical' => DeliveryFormat.physical,
    'hybrid' => DeliveryFormat.hybrid,
    _ => throw LiveBackendException('Unknown delivery format: $value'),
  };

  static String _deliveryToWire(DeliveryFormat format) => switch (format) {
    DeliveryFormat.online => 'online',
    DeliveryFormat.physical => 'physical',
    DeliveryFormat.hybrid => 'hybrid',
  };

  // Keep in sync with `_VERIFICATION_WIRE_TO_MODEL` in
  // scholarsphere_backend/app/schemas/provider_opportunity.py.
  static VerificationStatus _verificationFromWire(String value) =>
      switch (value) {
        'pending' => VerificationStatus.pending,
        'verified' => VerificationStatus.verified,
        'verificationExpired' => VerificationStatus.verificationExpired,
        'incomplete' => VerificationStatus.incomplete,
        'suspicious' => VerificationStatus.suspicious,
        'rejected' => VerificationStatus.rejected,
        'expired' => VerificationStatus.expired,
        'archived' => VerificationStatus.archived,
        _ => throw LiveBackendException(
          'Unknown verification status: $value',
        ),
      };

  static DateTime? _date(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  static String _dateString(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';

  Future<dynamic> _get(String path, {Map<String, String> query = const {}}) async {
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
      throw const LiveBackendException(
        'Sign in to manage opportunities.',
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
