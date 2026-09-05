import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/fraud_case.dart';
import '../domain/fraud_investigation_repository.dart';

/// Reads and writes real fraud-investigation case, evidence, and watchlist
/// data from the ScholarSphere Python backend. Live replacement for
/// [DemoFraudInvestigationRepository].
///
/// [createCase]'s risk score is never trusted as-is from the caller: this
/// repository unpacks [FraudCase.risk] back into the raw signal flags it
/// was built from (suspicious domain, risky link, etc. - each recoverable
/// from the non-zero magnitude constants
/// [DemoFraudInvestigationRepository]'s [RiskScoringService] uses) and
/// sends those, so the server always independently recomputes the actual
/// score and risk level rather than accepting a client-computed verdict.
/// [addNote]/[restrict]'s `investigatorId` and [appeal]'s `subjectId`
/// parameters are accepted for interface compatibility but never sent:
/// the server checks the caller's own verified identity against the
/// case's assigned investigator / subject, never a client-asserted one.
class ApiFraudInvestigationRepository implements FraudInvestigationRepository {
  ApiFraudInvestigationRepository({
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
  Future<FraudCase> createCase(FraudCase fraudCase) async {
    try {
      final risk = fraudCase.risk;
      final body = await _post('/fraud-investigation/cases', {
        'subject_type': fraudCase.subjectType.name,
        'subject_id': fraudCase.subjectId,
        'risk_input': {
          'provider_risk': risk.providerRisk,
          'source_risk': risk.sourceRisk,
          'user_behaviour_risk': risk.userBehaviourRisk,
          'suspicious_domain': risk.domainRisk > 0,
          'duplicate_account': risk.reasons.contains(
            'Possible duplicate account detected.',
          ),
          'risky_link': risk.linkRisk > 0,
          'payment_request': risk.paymentRisk > 0,
          'impersonation': risk.impersonationRisk > 0,
        },
      });
      return _toCase(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const FraudInvestigationFailure(
          'An open fraud case already exists for this subject.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<FraudCase> assign(String caseId, String investigatorId) async {
    try {
      final body = await _post('/fraud-investigation/cases/$caseId/assign', {
        'investigator_id': investigatorId,
      });
      return _toCase(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const FraudInvestigationFailure('Fraud case was not found.');
      }
      rethrow;
    }
  }

  @override
  Future<FraudCase> addEvidence(String caseId, FraudEvidence evidence) async {
    try {
      final body = await _post('/fraud-investigation/cases/$caseId/evidence', {
        'type': evidence.type,
        'location': evidence.location,
        'summary': evidence.summary,
      });
      return _toCase(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const FraudInvestigationFailure('Fraud case was not found.');
      }
      rethrow;
    }
  }

  @override
  Future<FraudCase> addNote(
    String caseId,
    String investigatorId,
    String note,
  ) async {
    try {
      final body = await _post('/fraud-investigation/cases/$caseId/notes', {
        'note': note,
      });
      return _toCase(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const FraudInvestigationFailure('Fraud case was not found.');
      }
      if (error.statusCode == 403) {
        throw const FraudInvestigationFailure(
          'Only the assigned investigator can add notes.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<FraudCase> restrict(String caseId, String investigatorId) async {
    try {
      final body = await _post(
        '/fraud-investigation/cases/$caseId/restrict',
        const {},
      );
      return _toCase(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const FraudInvestigationFailure('Fraud case was not found.');
      }
      if (error.statusCode == 409) {
        throw const FraudInvestigationFailure(
          'A restriction requires supporting evidence.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<FraudCase> appeal(
    String caseId,
    String subjectId,
    String reason,
  ) async {
    try {
      final body = await _post('/fraud-investigation/cases/$caseId/appeal', {
        'reason': reason,
      });
      return _toCase(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const FraudInvestigationFailure('Fraud case was not found.');
      }
      if (error.statusCode == 409 || error.statusCode == 403) {
        throw const FraudInvestigationFailure(
          'Only a restricted subject can appeal.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<void> addWatchlistEntry(WatchlistEntry entry) async {
    try {
      await _post('/fraud-investigation/watchlist', {
        'subject_type': entry.subjectType.name,
        'value': entry.value,
        'reason': entry.reason,
        'blocked': entry.blocked,
      });
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const FraudInvestigationFailure(
          'Watchlist entry already exists.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<bool> isBlocked(FraudSubjectType type, String value) async {
    final body = await _get(
      '/fraud-investigation/watchlist/${type.name}/blocked',
      {'value': value},
    );
    return body as bool;
  }

  @override
  Future<List<FraudCase>> queue() async {
    final body = await _get('/fraud-investigation/queue', const {});
    return (body as List<dynamic>)
        .map((item) => _toCase(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<FraudAnalytics> analytics() async {
    final body = await _get('/fraud-investigation/analytics', const {});
    final json = body as Map<String, dynamic>;
    return FraudAnalytics(
      openCases: json['open_cases'] as int,
      criticalCases: json['critical_cases'] as int,
      restrictedSubjects: json['restricted_subjects'] as int,
      watchlistEntries: json['watchlist_entries'] as int,
      bySubjectType: (json['by_subject_type'] as Map<String, dynamic>).map(
        (key, value) => MapEntry(_subjectTypeFromWire(key), value as int),
      ),
    );
  }

  FraudCase _toCase(Map<String, dynamic> json) {
    final risk = json['risk'] as Map<String, dynamic>;
    return FraudCase(
      id: json['id'] as String,
      subjectType: _subjectTypeFromWire(json['subject_type'] as String),
      subjectId: json['subject_id'] as String,
      risk: RiskScore(
        overall: risk['overall'] as int,
        level: InvestigationRiskLevel.values.firstWhere(
          (value) => value.name == risk['level'],
        ),
        providerRisk: risk['provider_risk'] as int,
        sourceRisk: risk['source_risk'] as int,
        userBehaviourRisk: risk['user_behaviour_risk'] as int,
        domainRisk: risk['domain_risk'] as int,
        linkRisk: risk['link_risk'] as int,
        paymentRisk: risk['payment_risk'] as int,
        impersonationRisk: risk['impersonation_risk'] as int,
        reasons: (risk['reasons'] as List<dynamic>).cast<String>(),
      ),
      status: FraudCaseStatus.values.firstWhere(
        (value) => value.name == json['status'],
      ),
      assignedInvestigatorId: json['assigned_investigator_id'] as String?,
      evidence: (json['evidence'] as List<dynamic>)
          .map((item) => _evidenceFromWire(item as Map<String, dynamic>))
          .toList(),
      investigatorNotes: (json['investigator_notes'] as List<dynamic>)
          .cast<String>(),
      createdAt: DateTime.parse(json['created_at'] as String),
      history: (json['history'] as List<dynamic>).cast<String>(),
      appealReason: json['appeal_reason'] as String?,
    );
  }

  FraudEvidence _evidenceFromWire(Map<String, dynamic> json) => FraudEvidence(
    id: json['id'] as String,
    type: json['type'] as String,
    location: json['location'] as String,
    summary: json['summary'] as String,
    collectedAt: DateTime.parse(json['collected_at'] as String),
    collectedBy: json['collected_by'] as String,
  );

  // Keep in sync with app/models/fraud_investigation.py's enum wire values.
  static FraudSubjectType _subjectTypeFromWire(String value) =>
      FraudSubjectType.values.firstWhere(
        (type) => type.name == value,
        orElse: () =>
            throw LiveBackendException('Unknown fraud subject type: $value'),
      );

  Future<dynamic> _get(String path, Map<String, String> query) async {
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
