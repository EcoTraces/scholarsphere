enum PasswordHashAlgorithm { argon2id, bcrypt }

abstract interface class PasswordSecurityGateway {
  PasswordHashAlgorithm get algorithm;

  Future<String> hash(String password);

  Future<bool> verify(String password, String encodedHash);

  Future<bool> wasUsedPreviously(String userId, String password);

  Future<void> storePasswordHistory(String userId, String encodedHash);
}

abstract interface class CaptchaVerifier {
  Future<bool> verify(String singleUseToken, String expectedAction);
}

abstract interface class SecretVault {
  Future<String> getSecret(String key);

  Future<void> rotateSecret(String key);
}

abstract interface class IpSecurityController {
  Future<bool> isAllowed(String ipAddress);

  Future<void> block(String ipAddress, Duration duration);
}

abstract final class TransportSecurityPolicy {
  static void requireHttps(Uri uri) {
    if (uri.scheme != 'https') {
      throw StateError('Production communications require HTTPS.');
    }
  }
}
