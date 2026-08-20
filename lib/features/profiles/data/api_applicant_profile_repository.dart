import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/applicant_profile.dart';
import '../domain/applicant_profile_repository.dart';

/// Reads and writes real, per-user applicant profile data from the
/// ScholarSphere Python backend (scholarsphere_backend/).
///
/// This is the live replacement for [DemoApplicantProfileRepository]. The
/// backend never persists [ApplicantProfile.documents]: the Dart type is
/// metadata-only (name/type/timestamp, no file path or URL), so there is
/// nothing real to store yet - it always round-trips as an empty list here.
/// Real file storage belongs to a dedicated Documents feature.
///
/// Every request is scoped to the caller's own Firebase UID from the
/// bearer token, never from a client-supplied `userId` parameter or the
/// `userId` embedded in a submitted [ApplicantProfile].
class ApiApplicantProfileRepository implements ApplicantProfileRepository {
  ApiApplicantProfileRepository({
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
  Future<ApplicantProfile?> getForUser(String userId) async {
    try {
      final body = await _get('/applicant-profiles/me');
      return _toProfile(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<void> save(ApplicantProfile profile) async {
    await _put('/applicant-profiles/me', {
      'full_name': profile.fullName,
      'nationality': profile.nationality,
      'country_of_residence': profile.countryOfResidence,
      'date_of_birth': _dateString(profile.dateOfBirth),
      'gender': profile.gender,
      'highest_qualification': profile.highestQualification,
      'degree_field': profile.degreeField,
      'academic_classification': profile.academicClassification,
      'graduation_year': profile.graduationYear,
      'work_experience_years': profile.workExperienceYears,
      'preferred_study_levels': profile.preferredStudyLevels,
      'preferred_countries': profile.preferredCountries,
      'areas_of_interest': profile.areasOfInterest,
      'english_test_status': _englishTestToWire(profile.englishTestStatus),
      'passport_status': _passportToWire(profile.passportStatus),
      'employment_status': _employmentToWire(profile.employmentStatus),
      'funding_preferences': profile.fundingPreferences,
      'special_eligibility_categories': profile.specialEligibilityCategories,
    });
  }

  @override
  Future<List<ApplicantProfile>> getAllForAdministration() async {
    final profiles = <ApplicantProfile>[];
    var page = 1;
    const pageSize = 100;
    while (true) {
      final body =
          await _get('/applicant-profiles/admin', {
                'page': '$page',
                'page_size': '$pageSize',
              })
              as Map<String, dynamic>;
      final items = (body['items'] as List<dynamic>)
          .map((item) => _toProfile(item as Map<String, dynamic>))
          .toList();
      profiles.addAll(items);
      if (items.length < pageSize) break;
      page += 1;
    }
    return profiles;
  }

  ApplicantProfile _toProfile(Map<String, dynamic> json) => ApplicantProfile(
    userId: json['user_id'] as String,
    fullName: json['full_name'] as String,
    nationality: json['nationality'] as String,
    countryOfResidence: json['country_of_residence'] as String,
    dateOfBirth: _date(json['date_of_birth']),
    gender: json['gender'] as String,
    highestQualification: json['highest_qualification'] as String,
    degreeField: json['degree_field'] as String,
    academicClassification: json['academic_classification'] as String,
    graduationYear: json['graduation_year'] as int?,
    workExperienceYears: (json['work_experience_years'] as num).toDouble(),
    preferredStudyLevels: (json['preferred_study_levels'] as List<dynamic>)
        .cast<String>(),
    preferredCountries: (json['preferred_countries'] as List<dynamic>)
        .cast<String>(),
    areasOfInterest: (json['areas_of_interest'] as List<dynamic>)
        .cast<String>(),
    englishTestStatus: _englishTestFromWire(
      json['english_test_status'] as String,
    ),
    passportStatus: _passportFromWire(json['passport_status'] as String),
    employmentStatus: _employmentFromWire(json['employment_status'] as String),
    fundingPreferences: (json['funding_preferences'] as List<dynamic>)
        .cast<String>(),
    specialEligibilityCategories:
        (json['special_eligibility_categories'] as List<dynamic>)
            .cast<String>(),
    documents: const [],
  );

  // Keep these three maps in sync with app/schemas/applicant_profile.py's
  // wire maps.
  static String _englishTestToWire(EnglishTestStatus value) => switch (value) {
    EnglishTestStatus.notTaken => 'notTaken',
    EnglishTestStatus.planned => 'planned',
    EnglishTestStatus.completed => 'completed',
    EnglishTestStatus.notRequired => 'notRequired',
  };

  static EnglishTestStatus _englishTestFromWire(String value) => switch (value) {
    'notTaken' => EnglishTestStatus.notTaken,
    'planned' => EnglishTestStatus.planned,
    'completed' => EnglishTestStatus.completed,
    'notRequired' => EnglishTestStatus.notRequired,
    _ => throw LiveBackendException('Unknown English test status: $value'),
  };

  static String _passportToWire(PassportStatus value) => switch (value) {
    PassportStatus.unavailable => 'unavailable',
    PassportStatus.applied => 'applied',
    PassportStatus.valid => 'valid',
    PassportStatus.expired => 'expired',
  };

  static PassportStatus _passportFromWire(String value) => switch (value) {
    'unavailable' => PassportStatus.unavailable,
    'applied' => PassportStatus.applied,
    'valid' => PassportStatus.valid,
    'expired' => PassportStatus.expired,
    _ => throw LiveBackendException('Unknown passport status: $value'),
  };

  static String _employmentToWire(EmploymentStatus value) => switch (value) {
    EmploymentStatus.student => 'student',
    EmploymentStatus.employed => 'employed',
    EmploymentStatus.selfEmployed => 'selfEmployed',
    EmploymentStatus.unemployed => 'unemployed',
    EmploymentStatus.other => 'other',
  };

  static EmploymentStatus _employmentFromWire(String value) => switch (value) {
    'student' => EmploymentStatus.student,
    'employed' => EmploymentStatus.employed,
    'selfEmployed' => EmploymentStatus.selfEmployed,
    'unemployed' => EmploymentStatus.unemployed,
    'other' => EmploymentStatus.other,
    _ => throw LiveBackendException('Unknown employment status: $value'),
  };

  static DateTime? _date(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  static String? _dateString(DateTime? date) => date == null
      ? null
      : '${date.year.toString().padLeft(4, '0')}-'
            '${date.month.toString().padLeft(2, '0')}-'
            '${date.day.toString().padLeft(2, '0')}';

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

  Future<dynamic> _put(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.put(uri, headers: headers, body: jsonEncode(body)),
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
        'Sign-in expired. Sign in again to view your profile.',
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
        'Sign in to view your profile.',
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
