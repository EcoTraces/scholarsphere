enum LoginOutcome { success, invalidCredentials, locked, blockedIp, mfaFailed }

enum SecurityAlertType {
  newDevice,
  suspiciousLogin,
  repeatedFailures,
  accountLocked,
  sessionRevoked,
  privilegedAction,
}

class DeviceIdentity {
  const DeviceIdentity({
    required this.id,
    required this.browser,
    required this.operatingSystem,
    required this.ipAddress,
  });

  final String id;
  final String browser;
  final String operatingSystem;
  final String ipAddress;
}

class LoginHistoryEntry {
  const LoginHistoryEntry({
    required this.id,
    required this.email,
    required this.occurredAt,
    required this.outcome,
    required this.device,
    required this.suspicious,
  });

  final String id;
  final String email;
  final DateTime occurredAt;
  final LoginOutcome outcome;
  final DeviceIdentity device;
  final bool suspicious;
}

class SecuritySession {
  const SecuritySession({
    required this.id,
    required this.userId,
    required this.device,
    required this.createdAt,
    required this.expiresAt,
    required this.lastActivityAt,
    required this.revokedAt,
    required this.strongAuthentication,
  });

  final String id;
  final String userId;
  final DeviceIdentity device;
  final DateTime createdAt;
  final DateTime expiresAt;
  final DateTime lastActivityAt;
  final DateTime? revokedAt;
  final bool strongAuthentication;

  bool isActiveAt(DateTime at) => revokedAt == null && expiresAt.isAfter(at);

  SecuritySession revoke(DateTime at) => SecuritySession(
    id: id,
    userId: userId,
    device: device,
    createdAt: createdAt,
    expiresAt: expiresAt,
    lastActivityAt: lastActivityAt,
    revokedAt: at,
    strongAuthentication: strongAuthentication,
  );
}

class SecurityAlert {
  const SecurityAlert({
    required this.id,
    required this.userId,
    required this.type,
    required this.message,
    required this.createdAt,
    required this.acknowledgedAt,
  });

  final String id;
  final String? userId;
  final SecurityAlertType type;
  final String message;
  final DateTime createdAt;
  final DateTime? acknowledgedAt;
}

class SecurityFailure implements Exception {
  const SecurityFailure(this.message);

  final String message;
}

abstract final class PasswordPolicy {
  static String? validate(String password) {
    if (password.length < 12) return 'Use at least 12 characters.';
    if (!RegExp('[A-Z]').hasMatch(password)) {
      return 'Add an uppercase letter.';
    }
    if (!RegExp('[a-z]').hasMatch(password)) {
      return 'Add a lowercase letter.';
    }
    if (!RegExp('[0-9]').hasMatch(password)) return 'Add a number.';
    if (!RegExp(r'[^A-Za-z0-9]').hasMatch(password)) {
      return 'Add a symbol.';
    }
    return null;
  }
}
