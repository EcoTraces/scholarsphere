import 'experience_preferences.dart';

abstract class ExperienceRepository {
  Future<ExperiencePreferences> getPreferences(String userId);
  Future<void> savePreferences(
    String userId,
    ExperiencePreferences preferences,
  );
  Future<void> saveTranslation(TranslationEntry entry);
  Future<String> translate(
    String key,
    SupportedLanguage language, {
    String? fallback,
  });
  Future<void> cacheOpportunity(String userId, String opportunityId);
  Future<void> removeCachedOpportunity(String userId, String opportunityId);
  Future<Set<String>> cachedOpportunities(String userId);
}
