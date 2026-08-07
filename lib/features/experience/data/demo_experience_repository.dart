import '../domain/experience_preferences.dart';
import '../domain/experience_repository.dart';

class DemoExperienceRepository implements ExperienceRepository {
  final Map<String, ExperiencePreferences> _preferences = {};
  final Map<String, TranslationEntry> _translations = {};
  final Map<String, Set<String>> _cache = {};

  @override
  Future<ExperiencePreferences> getPreferences(String userId) async =>
      _preferences[userId] ?? const ExperiencePreferences();

  @override
  Future<void> savePreferences(
    String userId,
    ExperiencePreferences preferences,
  ) async {
    if (preferences.textScale < 1 || preferences.textScale > 2) {
      throw ArgumentError('Text scale must be from 1.0 to 2.0.');
    }
    _preferences[userId] = preferences;
  }

  @override
  Future<void> saveTranslation(TranslationEntry entry) async {
    _translations['${entry.language.code}:${entry.key}'] = entry;
  }

  @override
  Future<String> translate(
    String key,
    SupportedLanguage language, {
    String? fallback,
  }) async => _translations['${language.code}:$key']?.value ?? fallback ?? key;

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
}
