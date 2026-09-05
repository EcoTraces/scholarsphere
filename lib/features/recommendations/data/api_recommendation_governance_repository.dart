import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/recommendation.dart';
import '../domain/recommendation_governance.dart';
import '../domain/recommendation_governance_repository.dart';

/// Reads and writes real recommendation-personalization data from the
/// ScholarSphere Python backend. Live replacement for
/// [DemoRecommendationGovernanceRepository].
///
/// [getFeedback], [recordFeedback], and [qualityReport] have no current UI
/// caller ([RecommendationControlsScreen] only uses controls/history), but
/// are implemented for interface completeness. [qualityReport] is
/// staff-only server-side since it aggregates across every user.
class ApiRecommendationGovernanceRepository
    implements RecommendationGovernanceRepository {
  ApiRecommendationGovernanceRepository({
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
  Future<PersonalizationControls> getControls(String userId) async {
    final body = await _get('/recommendations/controls');
    return _toControls(body as Map<String, dynamic>);
  }

  @override
  Future<void> saveControls(
    String userId,
    PersonalizationControls controls,
  ) async {
    await _put('/recommendations/controls', {
      'behavioural_recommendations_enabled':
          controls.behaviouralRecommendationsEnabled,
      'preferred_countries': controls.preferredCountries,
      'opportunity_categories': controls.opportunityCategories
          .map(_categoryToWire)
          .toList(),
      'hidden_opportunity_ids': controls.hiddenOpportunityIds.toList(),
    });
  }

  @override
  Future<void> recordHistory(RecommendationHistoryEntry entry) async {
    await _post('/recommendations/history', {
      'opportunity_id': entry.opportunityId,
      'score': entry.score,
      'labels': entry.labels.map(_labelToWire).toList(),
      'generated_at': entry.generatedAt.toUtc().toIso8601String(),
      'host_country': entry.hostCountry,
    });
  }

  @override
  Future<List<RecommendationHistoryEntry>> getHistory(String userId) async {
    final body = await _get('/recommendations/history');
    return (body as List<dynamic>)
        .map((item) => _toHistoryEntry(userId, item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> resetHistory(String userId) async {
    await _delete('/recommendations/history');
  }

  @override
  Future<void> recordFeedback(RecommendationFeedback feedback) async {
    await _post('/recommendations/feedback', {
      'opportunity_id': feedback.opportunityId,
      'type': _feedbackTypeToWire(feedback.type),
      'comment': feedback.comment,
    });
  }

  @override
  Future<List<RecommendationFeedback>> getFeedback(String userId) async {
    final body = await _get('/recommendations/feedback');
    return (body as List<dynamic>)
        .map((item) => _toFeedback(userId, item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<RecommendationQualityReport> qualityReport() async {
    final body = await _get('/recommendations/quality-report');
    final json = body as Map<String, dynamic>;
    return RecommendationQualityReport(
      generatedCount: json['generated_count'] as int,
      dismissalRate: (json['dismissal_rate'] as num).toDouble(),
      helpfulRate: (json['helpful_rate'] as num).toDouble(),
      countryDiversity: json['country_diversity'] as int,
      sponsoredShare: (json['sponsored_share'] as num).toDouble(),
      inappropriateReports: json['inappropriate_reports'] as int,
    );
  }

  PersonalizationControls _toControls(Map<String, dynamic> json) =>
      PersonalizationControls(
        behaviouralRecommendationsEnabled:
            json['behavioural_recommendations_enabled'] as bool,
        preferredCountries: (json['preferred_countries'] as List<dynamic>)
            .cast<String>(),
        opportunityCategories: (json['opportunity_categories'] as List<dynamic>)
            .map((value) => _categoryFromWire(value as String))
            .toSet(),
        hiddenOpportunityIds: (json['hidden_opportunity_ids'] as List<dynamic>)
            .cast<String>()
            .toSet(),
      );

  RecommendationHistoryEntry _toHistoryEntry(
    String userId,
    Map<String, dynamic> json,
  ) => RecommendationHistoryEntry(
    userId: userId,
    opportunityId: json['opportunity_id'] as String,
    score: json['score'] as int,
    labels: (json['labels'] as List<dynamic>)
        .map((value) => _labelFromWire(value as String))
        .toSet(),
    generatedAt: DateTime.parse(json['generated_at'] as String),
    hostCountry: json['host_country'] as String,
  );

  RecommendationFeedback _toFeedback(
    String userId,
    Map<String, dynamic> json,
  ) => RecommendationFeedback(
    userId: userId,
    opportunityId: json['opportunity_id'] as String,
    type: _feedbackTypeFromWire(json['type'] as String),
    createdAt: DateTime.parse(json['created_at'] as String),
    comment: json['comment'] as String?,
  );

  // Keep in sync with app/schemas/recommendation_governance.py's wire sets.
  static String _categoryToWire(RecommendationCategory category) =>
      category.name;

  static RecommendationCategory _categoryFromWire(String value) =>
      RecommendationCategory.values.firstWhere(
        (category) => category.name == value,
        orElse: () => throw LiveBackendException(
          'Unknown recommendation category: $value',
        ),
      );

  static String _labelToWire(RecommendationLabel label) => label.name;

  static RecommendationLabel _labelFromWire(String value) =>
      RecommendationLabel.values.firstWhere(
        (label) => label.name == value,
        orElse: () =>
            throw LiveBackendException('Unknown recommendation label: $value'),
      );

  static String _feedbackTypeToWire(RecommendationFeedbackType type) =>
      type.name;

  static RecommendationFeedbackType _feedbackTypeFromWire(String value) =>
      RecommendationFeedbackType.values.firstWhere(
        (type) => type.name == value,
        orElse: () => throw LiveBackendException(
          'Unknown recommendation feedback type: $value',
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

  Future<dynamic> _put(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.put(uri, headers: headers, body: jsonEncode(body)),
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
