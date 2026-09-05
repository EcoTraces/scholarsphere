import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../opportunities/domain/opportunity.dart';
import '../../security/domain/security_backend_contracts.dart';
import '../domain/collected_opportunity.dart';
import '../domain/opportunity_collection_repository.dart';

/// Reads and writes the real collection intake ledger from the
/// ScholarSphere Python backend. Live replacement for
/// [DemoOpportunityCollectionRepository].
///
/// [collect]'s `automated` flag is never trusted from the client - the
/// server re-derives it from `sourceType` itself (a caller could otherwise
/// falsely claim a feed-sourced record was manually entered to dodge the
/// approved-source registry check), and `approvedSource` is only ever
/// consulted for non-automated entries, where it is a staff record-keeping
/// label rather than a security gate. `collectedByUserId` is likewise
/// accepted for interface compatibility but never sent: the server always
/// records the caller's own verified identity.
class ApiOpportunityCollectionRepository
    implements OpportunityCollectionRepository {
  ApiOpportunityCollectionRepository({
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
  Future<List<CollectedOpportunity>> getIntakeLedger() async {
    final body = await _get('/collection/ledger');
    return (body as List<dynamic>)
        .map((item) => _toCollected(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<CollectedOpportunity> collect({
    required Opportunity opportunity,
    required CollectionSourceType sourceType,
    required String sourceLocation,
    required bool automated,
    required bool approvedSource,
    String? collectedByUserId,
  }) async {
    try {
      final body = await _post('/collection/collect', {
        'title': opportunity.title,
        'provider': opportunity.provider,
        'host_country': opportunity.hostCountry,
        'type': opportunity.type.name,
        'deadline': _dateOnly(opportunity.deadline),
        'application_open_date': _dateOnly(opportunity.applicationOpenDate),
        'official_source_url': opportunity.officialSourceUrl,
        'application_url': opportunity.applicationUrl,
        'summary': opportunity.summary,
        'source_type': sourceType.name,
        'source_location': sourceLocation,
        'approved_source': approvedSource,
      });
      return _toCollected(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const CollectionFailure(
          'Automated collection is restricted to approved registry sources.',
        );
      }
      rethrow;
    }
  }

  String? _dateOnly(DateTime? value) =>
      value == null ? null : value.toUtc().toIso8601String().split('T').first;

  CollectedOpportunity _toCollected(Map<String, dynamic> json) =>
      CollectedOpportunity(
        id: json['id'] as String,
        opportunityId: json['opportunity_id'] as String,
        sourceType: _sourceTypeFromWire(json['source_type'] as String),
        sourceLocation: json['source_location'] as String,
        discoveredAt: DateTime.parse(json['discovered_at'] as String),
        collectedByUserId: json['collected_by_user_id'] as String?,
        automated: json['automated'] as bool,
        approvedSource: json['approved_source'] as bool,
        // The backend always creates collected opportunities as pending
        // verification (matching DemoOpportunityCollectionRepository,
        // which never updates this ledger snapshot after creation either
        // - later verification decisions live on the opportunity itself,
        // not the intake ledger), so there is no live enum to map here.
        verificationStatus: VerificationStatus.pending,
      );

  // Keep in sync with app/models/collection.py's enum wire values.
  static CollectionSourceType _sourceTypeFromWire(String value) =>
      CollectionSourceType.values.firstWhere(
        (type) => type.name == value,
        orElse: () => throw LiveBackendException(
          'Unknown collection source type: $value',
        ),
      );

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
