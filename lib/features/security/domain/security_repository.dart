import 'security_models.dart';

abstract interface class SecurityRepository {
  Future<void> ensureLoginAllowed(String email, DeviceIdentity device);

  Future<void> recordLogin({
    required String email,
    required LoginOutcome outcome,
    required DeviceIdentity device,
    String? userId,
  });

  Future<SecuritySession> createSession({
    required String userId,
    required DeviceIdentity device,
    required bool strongAuthentication,
    required bool privileged,
  });

  Future<void> revokeSession(String sessionId);

  Future<void> revokeAllSessions(String userId);

  Future<List<SecuritySession>> getSessions(String userId);

  Future<List<LoginHistoryEntry>> getLoginHistory(String email);

  Future<List<SecurityAlert>> getAlerts(String userId);

  Future<void> enforceRateLimit(String key, {int limit = 60});
}
