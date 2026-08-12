import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:http/http.dart' as http;

import 'live_opportunity.dart';

/// A network failure talking to the live ScholarSphere discovery backend.
class LiveBackendException implements Exception {
  const LiveBackendException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

/// Reads real, human-verified opportunities from the ScholarSphere Python
/// backend (scholarsphere_backend/), which imports from Grants.gov,
/// Simpler.Grants.gov and the EU Funding & Tenders portal.
///
/// Every method here only reads data the backend has already published
/// after human verification (see the backend's verification/publication
/// pipeline). Nothing is written or auto-published from this client.
class LiveOpportunityRepository {
  LiveOpportunityRepository({
    String? baseUrl,
    http.Client? client,
    firebase.FirebaseAuth? auth,
  }) : baseUrl = baseUrl ?? _defaultBaseUrl,
       _client = client ?? http.Client(),
       _auth = auth ?? firebase.FirebaseAuth.instance;

  /// Override at build/run time with
  /// `--dart-define=SCHOLARSPHERE_API_BASE_URL=https://api.example.org/api/v1`.
  static const _defaultBaseUrl = String.fromEnvironment(
    'SCHOLARSPHERE_API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  final String baseUrl;
  final http.Client _client;
  final firebase.FirebaseAuth _auth;

  Future<LiveOpportunityPage> getPublished({
    String? keyword,
    String? country,
    int? closingWithinDays,
    int page = 1,
    int pageSize = 25,
  }) async {
    final query = <String, String>{
      'page': '$page',
      'page_size': '$pageSize',
      if (keyword != null && keyword.isNotEmpty) 'keyword': keyword,
      if (country != null && country.isNotEmpty) 'country': country,
      if (closingWithinDays != null)
        'closing_within_days': '$closingWithinDays',
    };
    final body = await _get('/opportunities', query);
    return LiveOpportunityPage.fromJson(body as Map<String, dynamic>);
  }

  Future<LiveOpportunity> getById(String id) async {
    final body = await _get('/opportunities/$id', const {});
    return LiveOpportunity.fromJson(body as Map<String, dynamic>);
  }

  Future<LiveOpportunityEvidence> getEvidence(String id) async {
    final body = await _get('/opportunities/$id/evidence', const {});
    return LiveOpportunityEvidence.fromJson(body as Map<String, dynamic>);
  }

  Future<List<VerificationHistoryItem>> getVerificationHistory(
    String id,
  ) async {
    final body = await _get(
      '/external-opportunities/opportunities/$id/verification-history',
      const {},
    );
    final items = (body as Map<String, dynamic>)['items'] as List<dynamic>;
    return items
        .map(
          (item) =>
              VerificationHistoryItem.fromJson(item as Map<String, dynamic>),
        )
        .toList();
  }

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
        'Sign-in expired. Sign in again to view live opportunities.',
        statusCode: 401,
      );
    }
    if (response.statusCode == 403) {
      throw const LiveBackendException(
        'Your account is not authorized to view live opportunities.',
        statusCode: 403,
      );
    }
    if (response.statusCode == 404) {
      throw const LiveBackendException(
        'That opportunity was not found or is no longer published.',
        statusCode: 404,
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
        'Sign in to view live opportunities.',
        statusCode: 401,
      );
    }
    final token = await user.getIdToken();
    return {'Authorization': 'Bearer $token', 'Accept': 'application/json'};
  }

  void dispose() => _client.close();
}
