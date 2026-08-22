import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/document_readiness.dart';
import '../domain/document_repository.dart';

/// Reads and writes real, per-user document metadata from the ScholarSphere
/// Python backend (scholarsphere_backend/).
///
/// This is the live replacement for [DemoDocumentRepository]. The actual
/// file bytes never pass through this class or the backend - callers must
/// upload to Firebase Storage first (see `ApplicantDocumentUpload`) and
/// pass the resulting Storage path via [UserDocument.storagePath] into
/// [add]. The backend validates that path is under the caller's own uid
/// folder before accepting it, and every other request is scoped to the
/// caller's own Firebase UID from the bearer token, never a client-supplied
/// `userId` parameter.
///
/// [grantProviderAccess] is owner-only self-service here. The backend
/// enforces a real precondition before recording the grant: the caller
/// must have an active (granted, not withdrawn) third-party-sharing
/// consent on file (see the Privacy feature), and the target provider
/// must exist - otherwise the request fails with a 409/404 surfaced as a
/// [LiveBackendException] with the backend's real error message. See the
/// backend route's docstring (app/api/routes/applicant_documents.py) for
/// the full rationale.
class ApiDocumentRepository implements DocumentRepository {
  ApiDocumentRepository({
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
  Future<List<UserDocument>> getForUser(String userId) async {
    final body = await _get('/applicant-documents/me');
    final items = body as List<dynamic>;
    return items
        .map((item) => _toDocument(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> add(UserDocument document) async {
    final storagePath = document.storagePath;
    if (storagePath == null) {
      throw ArgumentError(
        'UserDocument.storagePath is required - upload the file to Storage '
        'first via ApplicantDocumentUpload, then pass its path here.',
      );
    }
    await _post('/applicant-documents', {
      'type': _typeToWire(document.type),
      'file_name': document.fileName,
      'storage_path': storagePath,
    });
  }

  @override
  Future<void> remove(String userId, String documentId) async {
    await _delete('/applicant-documents/$documentId');
  }

  @override
  Future<void> grantProviderAccess({
    required String userId,
    required String documentId,
    required String providerId,
  }) async {
    await _post('/applicant-documents/$documentId/share', {
      'provider_id': providerId,
    });
  }

  UserDocument _toDocument(Map<String, dynamic> json) => UserDocument(
    id: json['id'] as String,
    ownerUserId: json['user_id'] as String,
    type: _typeFromWire(json['type'] as String),
    fileName: json['file_name'] as String,
    uploadedAt: DateTime.parse(json['uploaded_at'] as String),
    // Every real Firebase Storage object is encrypted at rest by GCS by
    // default - the backend doesn't round-trip this, it's a constant fact.
    encryptedAtRest: true,
    sharedWithProviderIds: (json['shared_with_provider_ids'] as List<dynamic>)
        .cast<String>()
        .toSet(),
  );

  // Keep in sync with app/schemas/applicant_document.py's wire map.
  static String _typeToWire(DocumentType type) => switch (type) {
    DocumentType.passport => 'passport',
    DocumentType.curriculumVitae => 'curriculumVitae',
    DocumentType.academicTranscript => 'academicTranscript',
    DocumentType.degreeCertificate => 'degreeCertificate',
    DocumentType.recommendationLetters => 'recommendationLetters',
    DocumentType.motivationLetter => 'motivationLetter',
    DocumentType.personalStatement => 'personalStatement',
    DocumentType.researchProposal => 'researchProposal',
    DocumentType.englishLanguageCertificate => 'englishLanguageCertificate',
    DocumentType.workExperienceLetter => 'workExperienceLetter',
    DocumentType.birthCertificate => 'birthCertificate',
    DocumentType.portfolio => 'portfolio',
    DocumentType.financialDocuments => 'financialDocuments',
  };

  static DocumentType _typeFromWire(String value) => switch (value) {
    'passport' => DocumentType.passport,
    'curriculumVitae' => DocumentType.curriculumVitae,
    'academicTranscript' => DocumentType.academicTranscript,
    'degreeCertificate' => DocumentType.degreeCertificate,
    'recommendationLetters' => DocumentType.recommendationLetters,
    'motivationLetter' => DocumentType.motivationLetter,
    'personalStatement' => DocumentType.personalStatement,
    'researchProposal' => DocumentType.researchProposal,
    'englishLanguageCertificate' => DocumentType.englishLanguageCertificate,
    'workExperienceLetter' => DocumentType.workExperienceLetter,
    'birthCertificate' => DocumentType.birthCertificate,
    'portfolio' => DocumentType.portfolio,
    'financialDocuments' => DocumentType.financialDocuments,
    _ => throw LiveBackendException('Unknown document type: $value'),
  };

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
        'Sign-in expired. Sign in again to view your documents.',
        statusCode: 401,
      );
    }
    if (response.statusCode >= 400) {
      throw LiveBackendException(
        _errorDetail(response.body) ??
            'The ScholarSphere backend returned an error.',
        statusCode: response.statusCode,
      );
    }
    if (response.body.isEmpty) return null;
    return jsonDecode(response.body);
  }

  // Matches the envelope app/core/errors.py wraps every HTTPException in:
  // {"error": {"message": "..."}}. Consent-blocked shares (409) and
  // unknown-provider shares (404) both carry a real, specific message here
  // - e.g. "Third-party access requires explicit active user consent." -
  // that's worth surfacing to the caller instead of a generic fallback.
  static String? _errorDetail(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        final detail = decoded['detail'] ?? decoded['error']?['message'];
        if (detail is String) return detail;
      }
    } on FormatException {
      // Fall through to the generic message.
    }
    return null;
  }

  Future<Map<String, String>> _headers() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const LiveBackendException(
        'Sign in to view your documents.',
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
