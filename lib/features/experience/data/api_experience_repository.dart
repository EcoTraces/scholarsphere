import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/experience_preferences.dart';
import '../domain/experience_repository.dart';

/// Reads and writes real accessibility/localization preferences from the
/// ScholarSphere Python backend. Live replacement for
/// [DemoExperienceRepository].
///
/// [cacheOpportunity]/[removeCachedOpportunity]/[cachedOpportunities] are
/// deliberately kept as a local, in-memory cache rather than backed by a
/// server round-trip: they exist specifically to support low-bandwidth/
/// offline access to previously-viewed opportunities, so routing them
/// through the network would defeat their own purpose. This mirrors
/// [DemoExperienceRepository]'s in-memory `Map` for the same methods,
/// except scoped per repository instance instead of per demo session.
class ApiExperienceRepository implements ExperienceRepository {
  ApiExperienceRepository({
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
  final Map<String, Set<String>> _cache = {};

  firebase.FirebaseAuth get _auth =>
      _authOverride ?? firebase.FirebaseAuth.instance;

  @override
  Future<ExperiencePreferences> getPreferences(String userId) async {
    final body = await _get('/experience/preferences');
    return _toPreferences(body as Map<String, dynamic>);
  }

  @override
  Future<void> savePreferences(
    String userId,
    ExperiencePreferences preferences,
  ) async {
    try {
      await _put('/experience/preferences', {
        'language': _languageToWire(preferences.language),
        'timezone': preferences.timezone,
        'currency_code': preferences.currencyCode,
        'country_code': preferences.countryCode,
        'text_scale': preferences.textScale,
        'high_contrast': preferences.highContrast,
        'screen_reader_optimized': preferences.screenReaderOptimized,
        'keyboard_navigation': preferences.keyboardNavigation,
        'low_bandwidth_mode': preferences.lowBandwidthMode,
        'compress_images': preferences.compressImages,
        'data_saving': preferences.dataSaving,
        'cache_saved_opportunities': preferences.cacheSavedOpportunities,
      });
    } on LiveBackendException catch (error) {
      if (error.statusCode == 422) {
        throw ArgumentError('Text scale must be from 1.0 to 2.0.');
      }
      rethrow;
    }
  }

  @override
  Future<void> saveTranslation(TranslationEntry entry) async {
    await _put(
      '/experience/translations/${_languageToWire(entry.language)}/${entry.key}',
      {'value': entry.value},
    );
  }

  @override
  Future<String> translate(
    String key,
    SupportedLanguage language, {
    String? fallback,
  }) async {
    final body = await _get(
      '/experience/translations/${_languageToWire(language)}/$key',
      fallback == null ? const {} : {'fallback': fallback},
    );
    return (body as Map<String, dynamic>)['value'] as String;
  }

  @override
  Future<void> cacheOpportunity(String userId, String opportunityId) async {
    final preferences = await getPreferences(userId);
    if (!preferences.cacheSavedOpportunities) return;
    _cache.putIfAbsent(userId, () => {}).add(opportunityId);
  }

  @override
  Future<void> removeCachedOpportunity(
    String userId,
    String opportunityId,
  ) async {
    _cache[userId]?.remove(opportunityId);
  }

  @override
  Future<Set<String>> cachedOpportunities(String userId) async =>
      Set.unmodifiable(_cache[userId] ?? const {});

  ExperiencePreferences _toPreferences(Map<String, dynamic> json) =>
      ExperiencePreferences(
        language: _languageFromWire(json['language'] as String),
        timezone: json['timezone'] as String,
        currencyCode: json['currency_code'] as String,
        countryCode: json['country_code'] as String,
        textScale: (json['text_scale'] as num).toDouble(),
        highContrast: json['high_contrast'] as bool,
        screenReaderOptimized: json['screen_reader_optimized'] as bool,
        keyboardNavigation: json['keyboard_navigation'] as bool,
        lowBandwidthMode: json['low_bandwidth_mode'] as bool,
        compressImages: json['compress_images'] as bool,
        dataSaving: json['data_saving'] as bool,
        cacheSavedOpportunities: json['cache_saved_opportunities'] as bool,
      );

  // Keep in sync with app/schemas/experience.py's wire map.
  static String _languageToWire(SupportedLanguage language) => switch (language) {
    SupportedLanguage.english => 'english',
    SupportedLanguage.french => 'french',
    SupportedLanguage.spanish => 'spanish',
    SupportedLanguage.arabic => 'arabic',
  };

  static SupportedLanguage _languageFromWire(String value) => switch (value) {
    'english' => SupportedLanguage.english,
    'french' => SupportedLanguage.french,
    'spanish' => SupportedLanguage.spanish,
    'arabic' => SupportedLanguage.arabic,
    _ => throw LiveBackendException('Unknown language: $value'),
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
