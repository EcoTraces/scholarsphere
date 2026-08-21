import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/taxonomy.dart';
import '../domain/taxonomy_repository.dart';

/// Reads and writes real canonical-taxonomy governance data from the
/// ScholarSphere Python backend. Live replacement for
/// [DemoTaxonomyRepository]. `actorId` parameters accepted by this
/// interface for [save]/[merge] are kept for signature compatibility but
/// not sent to the server: the backend derives the acting staff member
/// from the caller's verified auth token so an edit can never be
/// attributed to someone else.
class ApiTaxonomyRepository implements TaxonomyRepository {
  ApiTaxonomyRepository({
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
  Future<TaxonomyTerm> save(
    TaxonomyTerm term, {
    required String actorId,
    required String reason,
  }) async {
    try {
      final body = await _post('/taxonomy/terms', {
        'id': term.id,
        'type': _typeToWire(term.type),
        'canonical_name': term.canonicalName,
        'code': term.code,
        'synonyms': term.synonyms.toList(),
        'parent_id': term.parentId,
        'active': term.active,
        'reason': reason,
      });
      return _toTerm(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw StateError('A canonical or synonymous taxonomy term exists.');
      }
      rethrow;
    }
  }

  @override
  Future<TaxonomyTerm?> resolve(TaxonomyType type, String value) async {
    final body = await _get('/taxonomy/terms/resolve', {
      'type': _typeToWire(type),
      'value': value,
    });
    if (body == null) return null;
    return _toTerm(body as Map<String, dynamic>);
  }

  @override
  Future<List<TaxonomyTerm>> list(
    TaxonomyType type, {
    bool activeOnly = true,
  }) async {
    final body = await _get('/taxonomy/terms', {
      'type': _typeToWire(type),
      'active_only': activeOnly.toString(),
    });
    return (body as List<dynamic>)
        .map((item) => _toTerm(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<List<List<TaxonomyTerm>>> duplicateCandidates(TaxonomyType type) async {
    final body = await _get('/taxonomy/terms/duplicates', {
      'type': _typeToWire(type),
    });
    return (body as List<dynamic>)
        .map(
          (group) => (group as List<dynamic>)
              .map((item) => _toTerm(item as Map<String, dynamic>))
              .toList(),
        )
        .toList();
  }

  @override
  Future<TaxonomyTerm> merge({
    required String canonicalId,
    required Set<String> duplicateIds,
    required String actorId,
  }) async {
    try {
      final body = await _post('/taxonomy/terms/merge', {
        'canonical_id': canonicalId,
        'duplicate_ids': duplicateIds.toList(),
      });
      return _toTerm(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw StateError('Canonical term not found.');
      }
      rethrow;
    }
  }

  @override
  Future<List<TaxonomyVersion>> versions() async {
    final body = await _get('/taxonomy/versions');
    return (body as List<dynamic>)
        .map((item) => _toVersion(item as Map<String, dynamic>))
        .toList();
  }

  TaxonomyTerm _toTerm(Map<String, dynamic> json) => TaxonomyTerm(
    id: json['id'] as String,
    type: _typeFromWire(json['type'] as String),
    canonicalName: json['canonical_name'] as String,
    code: json['code'] as String?,
    synonyms: (json['synonyms'] as List<dynamic>).cast<String>().toSet(),
    parentId: json['parent_id'] as String?,
    active: json['active'] as bool,
    version: json['version'] as int,
    createdAt: DateTime.parse(json['created_at'] as String),
    updatedAt: DateTime.parse(json['updated_at'] as String),
  );

  TaxonomyVersion _toVersion(Map<String, dynamic> json) => TaxonomyVersion(
    version: json['version'] as int,
    createdAt: DateTime.parse(json['created_at'] as String),
    createdBy: json['created_by'] as String,
    reason: json['reason'] as String,
    termCount: json['term_count'] as int,
  );

  // Keep in sync with app/schemas/taxonomy.py's wire map.
  static String _typeToWire(TaxonomyType type) => switch (type) {
    TaxonomyType.country => 'country',
    TaxonomyType.region => 'region',
    TaxonomyType.continent => 'continent',
    TaxonomyType.nationality => 'nationality',
    TaxonomyType.institution => 'institution',
    TaxonomyType.organization => 'organization',
    TaxonomyType.degreeLevel => 'degreeLevel',
    TaxonomyType.academicField => 'academicField',
    TaxonomyType.opportunityType => 'opportunityType',
    TaxonomyType.fundingType => 'fundingType',
    TaxonomyType.language => 'language',
    TaxonomyType.currency => 'currency',
    TaxonomyType.qualification => 'qualification',
    TaxonomyType.industrySector => 'industrySector',
  };

  static TaxonomyType _typeFromWire(String value) => switch (value) {
    'country' => TaxonomyType.country,
    'region' => TaxonomyType.region,
    'continent' => TaxonomyType.continent,
    'nationality' => TaxonomyType.nationality,
    'institution' => TaxonomyType.institution,
    'organization' => TaxonomyType.organization,
    'degreeLevel' => TaxonomyType.degreeLevel,
    'academicField' => TaxonomyType.academicField,
    'opportunityType' => TaxonomyType.opportunityType,
    'fundingType' => TaxonomyType.fundingType,
    'language' => TaxonomyType.language,
    'currency' => TaxonomyType.currency,
    'qualification' => TaxonomyType.qualification,
    'industrySector' => TaxonomyType.industrySector,
    _ => throw LiveBackendException('Unknown taxonomy type: $value'),
  };

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
