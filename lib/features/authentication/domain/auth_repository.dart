import 'user_account.dart';

class AuthFailure implements Exception {
  const AuthFailure(this.message);

  final String message;

  @override
  String toString() => message;
}

abstract interface class AuthRepository {
  UserAccount? get currentUser;

  Future<UserAccount?> restoreSession();

  Future<UserAccount> signIn({required String email, required String password});

  Future<UserAccount> register({
    required String fullName,
    required String email,
    required String password,
    required UserRole role,
  });

  Future<UserAccount> createManagedAccount({
    required String fullName,
    required String email,
    required String temporaryPassword,
    required UserRole role,
  });

  Future<UserAccount> signInWithGoogle();

  Future<void> sendPasswordReset(String email);

  Future<void> sendEmailVerification();

  Future<UserAccount> confirmEmailVerification();

  Future<void> signOut();

  Future<List<UserAccount>> getAllForAdministration();

  Future<void> suspendAccount(String userId);
}
