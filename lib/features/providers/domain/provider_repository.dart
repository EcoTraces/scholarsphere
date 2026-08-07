import 'provider_profile.dart';

abstract class ProviderRepository {
  Future<ProviderProfile?> getForUser(String userId);
  Future<List<ProviderProfile>> getReviewQueue();
  Future<ProviderProfile> register(ProviderProfile profile);
  Future<ProviderProfile> review({
    required String providerId,
    required String officerId,
    required ProviderStatus decision,
    required ProviderReviewChecklist checklist,
    String? note,
  });
  Future<ProviderProfile> suspend(String providerId, String reason);
  Future<ProviderProfile> appeal(String providerId, String reason);
  Future<ProviderProfile> addAdministrator(
    String providerId,
    ProviderAdministrator administrator,
  );
  Future<bool> canPublish(String userId);
}

class ProviderFailure implements Exception {
  const ProviderFailure(this.message);
  final String message;
}
