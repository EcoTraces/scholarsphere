import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../domain/auth_repository.dart';
import '../domain/user_account.dart';

class FirebaseAuthRepository implements AuthRepository {
  FirebaseAuthRepository({
    firebase.FirebaseAuth? authentication,
    FirebaseFirestore? firestore,
    FirebaseFunctions? functions,
  }) : _authentication = authentication ?? firebase.FirebaseAuth.instance,
       _firestore = firestore ?? FirebaseFirestore.instance,
       _functions = functions ?? FirebaseFunctions.instance;

  final firebase.FirebaseAuth _authentication;
  final FirebaseFirestore _firestore;
  final FirebaseFunctions _functions;
  UserAccount? _currentUser;
  bool _googleInitialized = false;

  CollectionReference<Map<String, dynamic>> get _users =>
      _firestore.collection('users');

  @override
  UserAccount? get currentUser => _currentUser;

  @override
  Future<UserAccount?> restoreSession() async {
    final user = _authentication.currentUser;
    if (user == null) return null;
    try {
      await user.reload();
      final refreshed = _authentication.currentUser!;
      final account = await _loadAccount(refreshed);
      if (account.role == UserRole.applicant && !refreshed.emailVerified) {
        await _authentication.signOut();
        _currentUser = null;
        return null;
      }
      return account;
    } on AuthFailure {
      await _authentication.signOut();
      return null;
    }
  }

  @override
  Future<UserAccount> signIn({
    required String email,
    required String password,
  }) async {
    try {
      final credential = await _authentication.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      final user = credential.user;
      if (user == null) throw const AuthFailure('Sign-in did not complete.');
      await user.reload();
      return _loadAccount(_authentication.currentUser!);
    } on firebase.FirebaseAuthException catch (error) {
      throw AuthFailure(_authMessage(error));
    }
  }

  @override
  Future<UserAccount> register({
    required String fullName,
    required String email,
    required String password,
    required UserRole role,
  }) async {
    if (role != UserRole.applicant) {
      throw const AuthFailure('Only applicants can self-register.');
    }
    try {
      final credential = await _authentication.createUserWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      final user = credential.user;
      if (user == null) {
        throw const AuthFailure('Account registration did not complete.');
      }
      await user.updateDisplayName(fullName.trim());
      final account = UserAccount(
        id: user.uid,
        fullName: fullName.trim(),
        email: user.email!,
        role: UserRole.applicant,
        status: AccountStatus.pendingVerification,
        emailVerified: false,
      );
      await _users.doc(user.uid).set({
        ..._toFirestore(account),
        'createdAt': FieldValue.serverTimestamp(),
        'updatedAt': FieldValue.serverTimestamp(),
      });
      await user.sendEmailVerification();
      _currentUser = account;
      return account;
    } on firebase.FirebaseAuthException catch (error) {
      throw AuthFailure(_authMessage(error));
    }
  }

  @override
  Future<UserAccount> createManagedAccount({
    required String fullName,
    required String email,
    required String temporaryPassword,
    required UserRole role,
  }) async {
    if (role == UserRole.applicant) {
      throw const AuthFailure(
        'Applicants must create and verify their own accounts.',
      );
    }
    try {
      final result = await _functions
          .httpsCallable('createManagedUser')
          .call<Map<String, dynamic>>({
            'fullName': fullName.trim(),
            'email': email.trim().toLowerCase(),
            'temporaryPassword': temporaryPassword,
            'role': role.name,
          });
      return _fromMap(result.data);
    } on FirebaseFunctionsException catch (error) {
      throw AuthFailure(error.message ?? 'The account could not be created.');
    }
  }

  @override
  Future<UserAccount> signInWithGoogle() async {
    try {
      late final firebase.UserCredential credential;
      if (kIsWeb) {
        credential = await _authentication.signInWithPopup(
          firebase.GoogleAuthProvider(),
        );
      } else {
        if (!_googleInitialized) {
          await GoogleSignIn.instance.initialize();
          _googleInitialized = true;
        }
        final googleUser = await GoogleSignIn.instance.authenticate();
        final googleAuthentication = googleUser.authentication;
        credential = await _authentication.signInWithCredential(
          firebase.GoogleAuthProvider.credential(
            idToken: googleAuthentication.idToken,
          ),
        );
      }
      final user = credential.user;
      if (user == null) {
        throw const AuthFailure('Google sign-in did not complete.');
      }
      final existing = await _users.doc(user.uid).get();
      if (!existing.exists) {
        await _users.doc(user.uid).set({
          ..._toFirestore(
            UserAccount(
              id: user.uid,
              fullName: user.displayName ?? 'ScholarSphere Applicant',
              email: user.email!,
              role: UserRole.applicant,
              status: AccountStatus.active,
              emailVerified: true,
            ),
          ),
          'createdAt': FieldValue.serverTimestamp(),
          'updatedAt': FieldValue.serverTimestamp(),
        });
      }
      return _loadAccount(user);
    } on firebase.FirebaseAuthException catch (error) {
      throw AuthFailure(_authMessage(error));
    } on GoogleSignInException catch (error) {
      throw AuthFailure(error.description ?? 'Google sign-in was cancelled.');
    }
  }

  @override
  Future<void> sendPasswordReset(String email) async {
    try {
      await _authentication.sendPasswordResetEmail(email: email.trim());
    } on firebase.FirebaseAuthException catch (error) {
      if (error.code != 'user-not-found') {
        throw AuthFailure(_authMessage(error));
      }
    }
  }

  @override
  Future<void> sendEmailVerification() async {
    final user = _authentication.currentUser;
    if (user == null) {
      throw const AuthFailure('No account is awaiting verification.');
    }
    try {
      await user.sendEmailVerification();
    } on firebase.FirebaseAuthException catch (error) {
      throw AuthFailure(_authMessage(error));
    }
  }

  @override
  Future<UserAccount> confirmEmailVerification() async {
    final user = _authentication.currentUser;
    if (user == null) {
      throw const AuthFailure('No account is awaiting verification.');
    }
    await user.reload();
    final refreshed = _authentication.currentUser!;
    if (!refreshed.emailVerified) {
      throw const AuthFailure(
        'Email is not verified yet. Open the link in your email and try again.',
      );
    }
    await _users.doc(refreshed.uid).update({
      'emailVerified': true,
      'status': AccountStatus.active.name,
      'updatedAt': FieldValue.serverTimestamp(),
    });
    return _loadAccount(refreshed);
  }

  @override
  Future<void> signOut() async {
    if (!kIsWeb && _googleInitialized) {
      await GoogleSignIn.instance.signOut();
    }
    await _authentication.signOut();
    _currentUser = null;
  }

  @override
  Future<List<UserAccount>> getAllForAdministration() async {
    try {
      final snapshot = await _users.orderBy('fullName').get();
      return snapshot.docs.map((document) => _fromMap(document.data())).toList();
    } on FirebaseException catch (error) {
      throw AuthFailure(error.message ?? 'User accounts could not be loaded.');
    }
  }

  @override
  Future<void> suspendAccount(String userId) async {
    try {
      await _functions
          .httpsCallable('suspendUser')
          .call<Map<String, dynamic>>({
            'userId': userId,
          });
    } on FirebaseFunctionsException catch (error) {
      throw AuthFailure(error.message ?? 'The account could not be suspended.');
    }
  }

  Future<UserAccount> _loadAccount(firebase.User user) async {
    final document = await _users.doc(user.uid).get();
    if (!document.exists) {
      throw const AuthFailure(
        'Your ScholarSphere profile is missing. Contact support.',
      );
    }
    var account = _fromMap(document.data()!);
    if (user.emailVerified && !account.emailVerified) {
      await _users.doc(user.uid).update({
        'emailVerified': true,
        'status': AccountStatus.active.name,
        'updatedAt': FieldValue.serverTimestamp(),
      });
      account = UserAccount(
        id: account.id,
        fullName: account.fullName,
        email: account.email,
        role: account.role,
        status: AccountStatus.active,
        emailVerified: true,
        twoFactorEnabled: account.twoFactorEnabled,
        marketingEmailsEnabled: account.marketingEmailsEnabled,
        deadlineNotificationsEnabled: account.deadlineNotificationsEnabled,
      );
    }
    if (account.status == AccountStatus.suspended) {
      await _authentication.signOut();
      throw const AuthFailure('This account is suspended.');
    }
    _currentUser = account;
    return account;
  }

  static Map<String, dynamic> _toFirestore(UserAccount account) => {
    'uid': account.id,
    'fullName': account.fullName,
    'email': account.email,
    'role': account.role.name,
    'status': account.status.name,
    'emailVerified': account.emailVerified,
    'twoFactorEnabled': account.twoFactorEnabled,
    'marketingEmailsEnabled': account.marketingEmailsEnabled,
    'deadlineNotificationsEnabled': account.deadlineNotificationsEnabled,
  };

  static UserAccount _fromMap(Map<String, dynamic> data) => UserAccount(
    id: data['uid'] as String,
    fullName: data['fullName'] as String,
    email: data['email'] as String,
    role: UserRole.values.byName(data['role'] as String),
    status: AccountStatus.values.byName(data['status'] as String),
    emailVerified: data['emailVerified'] as bool? ?? false,
    twoFactorEnabled: data['twoFactorEnabled'] as bool? ?? false,
    marketingEmailsEnabled: data['marketingEmailsEnabled'] as bool? ?? false,
    deadlineNotificationsEnabled:
        data['deadlineNotificationsEnabled'] as bool? ?? true,
  );

  static String _authMessage(firebase.FirebaseAuthException error) =>
      switch (error.code) {
        'email-already-in-use' => 'An account already exists for this email.',
        'invalid-credential' ||
        'user-not-found' ||
        'wrong-password' => 'The email or password is incorrect.',
        'invalid-email' => 'Enter a valid email address.',
        'weak-password' => 'Choose a stronger password.',
        'too-many-requests' => 'Too many attempts. Try again later.',
        'user-disabled' => 'This account has been suspended.',
        _ => error.message ?? 'Authentication could not be completed.',
      };
}
