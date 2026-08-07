import '../domain/security_models.dart';
import '../domain/security_repository.dart';

class DemoSecurityRepository implements SecurityRepository {
  DemoSecurityRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final List<LoginHistoryEntry> _history = [];
  final Map<String, SecuritySession> _sessions = {};
  final List<SecurityAlert> _alerts = [];
  final Map<String, List<DateTime>> _rateEvents = {};

  @override
  Future<void> ensureLoginAllowed(String email, DeviceIdentity device) async {
    final now = _clock();
    final failures = _history.where(
      (entry) =>
          entry.email.toLowerCase() == email.toLowerCase() &&
          entry.outcome == LoginOutcome.invalidCredentials &&
          entry.occurredAt.isAfter(now.subtract(const Duration(minutes: 15))),
    );
    if (failures.length >= 5) {
      throw const SecurityFailure(
        'Account temporarily locked after repeated failed attempts.',
      );
    }
    await enforceRateLimit('login:${device.ipAddress}', limit: 20);
  }

  @override
  Future<void> recordLogin({
    required String email,
    required LoginOutcome outcome,
    required DeviceIdentity device,
    String? userId,
  }) async {
    final now = _clock();
    final previousDevices = _history
        .where(
          (entry) =>
              entry.email.toLowerCase() == email.toLowerCase() &&
              entry.outcome == LoginOutcome.success,
        )
        .map((entry) => entry.device.id)
        .toSet();
    final newDevice =
        outcome == LoginOutcome.success && !previousDevices.contains(device.id);
    final suspicious = newDevice && previousDevices.isNotEmpty;
    _history.add(
      LoginHistoryEntry(
        id: 'login-${now.microsecondsSinceEpoch}-${_history.length}',
        email: email.toLowerCase(),
        occurredAt: now,
        outcome: outcome,
        device: device,
        suspicious: suspicious,
      ),
    );
    if (outcome == LoginOutcome.invalidCredentials && userId != null) {
      final recentFailures = _history.where(
        (entry) =>
            entry.email == email.toLowerCase() &&
            entry.outcome == LoginOutcome.invalidCredentials &&
            entry.occurredAt.isAfter(now.subtract(const Duration(minutes: 15))),
      );
      if (recentFailures.length == 5) {
        _alerts.add(
          SecurityAlert(
            id: 'alert-lock-${now.microsecondsSinceEpoch}',
            userId: userId,
            type: SecurityAlertType.accountLocked,
            message: 'Your account was temporarily locked after failed logins.',
            createdAt: now,
            acknowledgedAt: null,
          ),
        );
      }
    }
    if (newDevice && userId != null) {
      _alerts.add(
        SecurityAlert(
          id: 'alert-${now.microsecondsSinceEpoch}',
          userId: userId,
          type: suspicious
              ? SecurityAlertType.suspiciousLogin
              : SecurityAlertType.newDevice,
          message: suspicious
              ? 'A login from a new device requires review.'
              : 'Your account was accessed from a new device.',
          createdAt: now,
          acknowledgedAt: null,
        ),
      );
    }
  }

  @override
  Future<SecuritySession> createSession({
    required String userId,
    required DeviceIdentity device,
    required bool strongAuthentication,
    required bool privileged,
  }) async {
    final now = _clock();
    if (privileged && !strongAuthentication) {
      throw const SecurityFailure(
        'Privileged sessions require multi-factor authentication.',
      );
    }
    final session = SecuritySession(
      id: 'session-${now.microsecondsSinceEpoch}-${_sessions.length}',
      userId: userId,
      device: device,
      createdAt: now,
      expiresAt: now.add(
        privileged ? const Duration(minutes: 15) : const Duration(hours: 8),
      ),
      lastActivityAt: now,
      revokedAt: null,
      strongAuthentication: strongAuthentication,
    );
    _sessions[session.id] = session;
    return session;
  }

  @override
  Future<void> revokeSession(String sessionId) async {
    final session = _sessions[sessionId];
    if (session != null) _sessions[sessionId] = session.revoke(_clock());
  }

  @override
  Future<void> revokeAllSessions(String userId) async {
    for (final entry in _sessions.entries.toList()) {
      if (entry.value.userId == userId && entry.value.revokedAt == null) {
        _sessions[entry.key] = entry.value.revoke(_clock());
      }
    }
  }

  @override
  Future<List<SecuritySession>> getSessions(String userId) async =>
      _sessions.values.where((item) => item.userId == userId).toList();

  @override
  Future<List<LoginHistoryEntry>> getLoginHistory(String email) async =>
      _history
          .where((item) => item.email.toLowerCase() == email.toLowerCase())
          .toList()
        ..sort((left, right) => right.occurredAt.compareTo(left.occurredAt));

  @override
  Future<List<SecurityAlert>> getAlerts(String userId) async => _alerts
      .where((item) => item.userId == null || item.userId == userId)
      .toList();

  @override
  Future<void> enforceRateLimit(String key, {int limit = 60}) async {
    final now = _clock();
    final events = _rateEvents.putIfAbsent(key, () => []);
    events.removeWhere(
      (event) => event.isBefore(now.subtract(const Duration(minutes: 1))),
    );
    if (events.length >= limit) {
      throw const SecurityFailure('Too many requests. Try again later.');
    }
    events.add(now);
  }
}
