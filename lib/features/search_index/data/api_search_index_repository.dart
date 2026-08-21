import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../opportunities/domain/opportunity.dart';
import '../../search/domain/opportunity_filter.dart';
import '../../security/domain/security_backend_contracts.dart';
import '../domain/search_index.dart';
import '../domain/search_index_repository.dart';

/// Reads and writes real search-index data from the ScholarSphere Python
/// backend. Live replacement for [DemoSearchIndexRepository].
///
/// Unlike the demo, [synchronize]/[upsert] never trust the client-supplied
/// opportunity snapshot at face value: the server independently re-checks
/// each opportunity id against the real, published external_opportunities
/// table before storing it, so a caller cannot poison the shared search
/// index with fabricated or already-hidden listings. [synchronize] also
/// never prunes entries missing from the caller's own batch (only the
/// staff-only [rebuild] does a full prune+resync) - a self-service caller
/// controls only what they add, not what disappears for every other user.
class ApiSearchIndexRepository implements SearchIndexRepository {
  ApiSearchIndexRepository({
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
  Future<void> synchronize(Iterable<Opportunity> opportunities) async {
    await _post('/search-index/synchronize', {
      'opportunities': opportunities.map(_opportunityToJson).toList(),
    });
  }

  @override
  Future<void> upsert(Opportunity opportunity) async {
    await _post('/search-index/opportunities', _opportunityToJson(opportunity));
  }

  @override
  Future<void> remove(String opportunityId) async {
    await _delete('/search-index/opportunities/$opportunityId');
  }

  @override
  Future<int> rebuild(Iterable<Opportunity> opportunities) async {
    final body = await _post('/search-index/rebuild', {
      'opportunities': opportunities.map(_opportunityToJson).toList(),
    });
    return body as int;
  }

  @override
  Future<DiscoverySearchResult> search(DiscoverySearchRequest request) async {
    try {
      final body = await _post('/search-index/search', {
        'query': request.query,
        'filter': _filterToJson(request.filter),
        'page': request.page,
        'page_size': request.pageSize,
        'eligibility_scores': request.eligibilityScores,
        'source_trust_scores': request.sourceTrustScores,
      });
      return _toResult(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 422) {
        throw ArgumentError('Invalid search pagination.');
      }
      rethrow;
    }
  }

  @override
  Future<List<String>> autocomplete(String prefix, {int limit = 8}) async {
    final body = await _get('/search-index/autocomplete', {
      'prefix': prefix,
      'limit': limit.toString(),
    });
    return (body as List<dynamic>).cast<String>();
  }

  @override
  Future<List<SearchHistoryEntry>> history(String userId) async {
    final body = await _get('/search-index/history');
    return (body as List<dynamic>)
        .map((item) => _toHistoryEntry(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> clearHistory(String userId) async {
    await _delete('/search-index/history');
  }

  @override
  Future<List<PopularSearch>> popularSearches({int limit = 10}) async {
    final body = await _get('/search-index/popular-searches', {
      'limit': limit.toString(),
    });
    return (body as List<dynamic>)
        .map(
          (item) => PopularSearch(
            query: (item as Map<String, dynamic>)['query'] as String,
            count: item['count'] as int,
          ),
        )
        .toList();
  }

  Map<String, dynamic> _opportunityToJson(Opportunity opportunity) => {
    'id': opportunity.id,
    'title': opportunity.title,
    'provider': opportunity.provider,
    'hostInstitution': opportunity.hostInstitution,
    'hostCountry': opportunity.hostCountry,
    'type': opportunity.type.name,
    'funding': opportunity.funding.name,
    'deadline': opportunity.deadline.toUtc().toIso8601String(),
    'applicationOpenDate': opportunity.applicationOpenDate
        .toUtc()
        .toIso8601String(),
    'verificationStatus': opportunity.verificationStatus.name,
    'lastVerifiedAt': opportunity.lastVerifiedAt?.toUtc().toIso8601String(),
    'officialSourceUrl': opportunity.officialSourceUrl,
    'applicationUrl': opportunity.applicationUrl,
    'eligibleNationalities': opportunity.eligibleNationalities,
    'studyLevels': opportunity.studyLevels,
    'fieldsOfStudy': opportunity.fieldsOfStudy,
    'summary': opportunity.summary,
    'benefits': opportunity.benefits,
    'eligibilityRequirements': opportunity.eligibilityRequirements,
    'requiredDocuments': opportunity.requiredDocuments,
    'applicationProcedure': opportunity.applicationProcedure,
    'languageRequirements': opportunity.languageRequirements,
    'minimumAge': opportunity.minimumAge,
    'maximumAge': opportunity.maximumAge,
    'workExperienceYearsRequired': opportunity.workExperienceYearsRequired,
    'contactInformation': opportunity.contactInformation,
    'availablePositions': opportunity.availablePositions,
    'deliveryFormat': opportunity.deliveryFormat.name,
    'applicationFee': opportunity.applicationFee,
  };

  Opportunity _opportunityFromJson(Map<String, dynamic> json) => Opportunity(
    id: json['id'] as String,
    title: json['title'] as String,
    provider: json['provider'] as String,
    hostInstitution: json['hostInstitution'] as String,
    hostCountry: json['hostCountry'] as String,
    type: _typeFromWire(json['type'] as String),
    funding: _fundingFromWire(json['funding'] as String),
    deadline: DateTime.parse(json['deadline'] as String),
    applicationOpenDate: DateTime.parse(json['applicationOpenDate'] as String),
    verificationStatus: _statusFromWire(json['verificationStatus'] as String),
    lastVerifiedAt: _dateTime(json['lastVerifiedAt']),
    officialSourceUrl: json['officialSourceUrl'] as String,
    applicationUrl: json['applicationUrl'] as String,
    eligibleNationalities: (json['eligibleNationalities'] as List<dynamic>)
        .cast<String>(),
    studyLevels: (json['studyLevels'] as List<dynamic>).cast<String>(),
    fieldsOfStudy: (json['fieldsOfStudy'] as List<dynamic>).cast<String>(),
    summary: json['summary'] as String,
    benefits: (json['benefits'] as List<dynamic>).cast<String>(),
    eligibilityRequirements:
        (json['eligibilityRequirements'] as List<dynamic>).cast<String>(),
    requiredDocuments: (json['requiredDocuments'] as List<dynamic>)
        .cast<String>(),
    applicationProcedure: (json['applicationProcedure'] as List<dynamic>)
        .cast<String>(),
    languageRequirements: (json['languageRequirements'] as List<dynamic>)
        .cast<String>(),
    minimumAge: json['minimumAge'] as int?,
    maximumAge: json['maximumAge'] as int?,
    workExperienceYearsRequired:
        (json['workExperienceYearsRequired'] as num?)?.toDouble(),
    contactInformation: json['contactInformation'] as String,
    availablePositions: json['availablePositions'] as int?,
    deliveryFormat: _deliveryFromWire(json['deliveryFormat'] as String),
    applicationFee: (json['applicationFee'] as num?)?.toDouble(),
  );

  Map<String, dynamic> _filterToJson(OpportunityFilter filter) => {
    'type': filter.type?.name,
    'country': filter.country,
    'region': filter.region?.name,
    'provider': filter.provider,
    'field': filter.field,
    'study_level': filter.studyLevel,
    'funding': filter.funding?.name,
    'no_application_fee': filter.noApplicationFee,
    'eligible_nationality': filter.eligibleNationality,
    'deadline_window': filter.deadlineWindow.name,
    'delivery_format': filter.deliveryFormat?.name,
    'applicant_age': filter.applicantAge,
    'available_work_experience_years': filter.availableWorkExperienceYears,
    'language': filter.language,
    'verified_only': filter.verifiedOnly,
    'availability': filter.availability.name,
  };

  DiscoverySearchResult _toResult(Map<String, dynamic> json) =>
      DiscoverySearchResult(
        hits: (json['hits'] as List<dynamic>)
            .map((item) => _toHit(item as Map<String, dynamic>))
            .toList(),
        total: json['total'] as int,
        facets: _toFacets(json['facets'] as Map<String, dynamic>),
        suggestions: (json['suggestions'] as List<dynamic>).cast<String>(),
        page: json['page'] as int,
        pageSize: json['page_size'] as int,
      );

  SearchHit _toHit(Map<String, dynamic> json) => SearchHit(
    opportunity: _opportunityFromJson(json['opportunity'] as Map<String, dynamic>),
    score: (json['score'] as num).toDouble(),
    matchedTerms: (json['matched_terms'] as List<dynamic>).cast<String>(),
  );

  SearchFacets _toFacets(Map<String, dynamic> json) => SearchFacets(
    countries: (json['countries'] as Map<String, dynamic>).cast<String, int>(),
    funding: (json['funding'] as Map<String, dynamic>).cast<String, int>(),
    studyLevels: (json['study_levels'] as Map<String, dynamic>)
        .cast<String, int>(),
    institutions: (json['institutions'] as Map<String, dynamic>)
        .cast<String, int>(),
  );

  SearchHistoryEntry _toHistoryEntry(Map<String, dynamic> json) =>
      SearchHistoryEntry(
        userId: json['user_id'] as String,
        query: json['query'] as String,
        resultCount: json['result_count'] as int,
        searchedAt: DateTime.parse(json['searched_at'] as String),
      );

  static DateTime? _dateTime(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  static OpportunityType _typeFromWire(String value) =>
      OpportunityType.values.firstWhere(
        (item) => item.name == value,
        orElse: () => throw LiveBackendException('Unknown opportunity type: $value'),
      );

  static FundingType _fundingFromWire(String value) =>
      FundingType.values.firstWhere(
        (item) => item.name == value,
        orElse: () => throw LiveBackendException('Unknown funding type: $value'),
      );

  static VerificationStatus _statusFromWire(String value) =>
      VerificationStatus.values.firstWhere(
        (item) => item.name == value,
        orElse: () =>
            throw LiveBackendException('Unknown verification status: $value'),
      );

  static DeliveryFormat _deliveryFromWire(String value) =>
      DeliveryFormat.values.firstWhere(
        (item) => item.name == value,
        orElse: () => throw LiveBackendException('Unknown delivery format: $value'),
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

  Future<dynamic> _delete(String path) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(() => _client.delete(uri, headers: headers));
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
