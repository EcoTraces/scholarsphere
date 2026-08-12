import '../domain/auth_repository.dart';
import '../domain/user_account.dart';
import '../../security/data/demo_security_repository.dart';
import '../../security/domain/access_control.dart';
import '../../security/domain/security_models.dart';
import '../../security/domain/security_repository.dart';
import '../../audit/domain/audit_record.dart';
import '../../audit/domain/audit_repository.dart';

class DemoAuthRepository implements AuthRepository {
  DemoAuthRepository({
    SecurityRepository? securityRepository,
    this.auditRepository,
    String? bootstrapAdminEmail,
    String? bootstrapAdminPassword,
  }) : securityRepository = securityRepository ?? DemoSecurityRepository() {
    if (bootstrapAdminEmail != null && bootstrapAdminPassword != null) {
      final email = bootstrapAdminEmail.trim().toLowerCase();
      _accounts[email] = (
        account: UserAccount(
          id: 'test-administrator',
          fullName: 'Test Administrator',
          email: email,
          role: UserRole.administrator,
          status: AccountStatus.active,
          emailVerified: true,
          twoFactorEnabled: true,
        ),
        password: bootstrapAdminPassword,
      );
    }
  }

  final SecurityRepository securityRepository;
  final AuditRepository? auditRepository;
  UserAccount? _currentUser;
  String? _currentSessionId;

  static const _demoDevice = DeviceIdentity(
    id: 'scholarsphere-demo-device',
    browser: 'Flutter client',
    operatingSystem: 'Current device',
    ipAddress: '127.0.0.1',
  );

  final Map<String, ({UserAccount account, String password})> _accounts = {};

  @override
  UserAccount? get currentUser => _currentUser;

  @override
  Future<UserAccount?> restoreSession() async => _currentUser;

  @override
  Future<UserAccount> signIn({
    required String email,
    required String password,
  }) async {
    final normalizedEmail = email.trim().toLowerCase();
    try {
      await securityRepository.ensureLoginAllowed(normalizedEmail, _demoDevice);
    } on SecurityFailure catch (failure) {
      throw AuthFailure(failure.message);
    }
    final record = _accounts[normalizedEmail];
    if (record == null || record.password != password) {
      await securityRepository.recordLogin(
        email: normalizedEmail,
        outcome: LoginOutcome.invalidCredentials,
        device: _demoDevice,
        userId: record?.account.id,
      );
      await auditRepository?.append(
        actorId: record?.account.id ?? 'anonymous',
        actorRole: record?.account.role.name ?? 'anonymous',
        action: AuditAction.failedLogin,
        entityType: 'account',
        entityId: normalizedEmail,
        result: AuditResult.failure,
        failureReason: 'Invalid credentials',
        correlationId: 'login-${DateTime.now().microsecondsSinceEpoch}',
        ipAddress: _demoDevice.ipAddress,
        deviceInformation:
            '${_demoDevice.browser} on ${_demoDevice.operatingSystem}',
      );
      throw const AuthFailure('The email or password is incorrect.');
    }
    if (record.account.status == AccountStatus.suspended) {
      throw const AuthFailure(
        'This account is suspended. Contact ScholarSphere support.',
      );
    }
    if (!record.account.emailVerified) {
      _currentUser = record.account;
      return record.account;
    }
    if (!record.account.canSignIn) {
      throw const AuthFailure('This account is not active.');
    }
    final privileged = AccessControlPolicy.requiresStrongAuthentication(
      record.account.role,
    );
    try {
      final session = await securityRepository.createSession(
        userId: record.account.id,
        device: _demoDevice,
        strongAuthentication: record.account.twoFactorEnabled,
        privileged: privileged,
      );
      _currentSessionId = session.id;
    } on SecurityFailure catch (failure) {
      throw AuthFailure(failure.message);
    }
    await securityRepository.recordLogin(
      email: normalizedEmail,
      outcome: LoginOutcome.success,
      device: _demoDevice,
      userId: record.account.id,
    );
    _currentUser = record.account;
    await auditRepository?.append(
      actorId: record.account.id,
      actorRole: record.account.role.name,
      action: AuditAction.login,
      entityType: 'session',
      entityId: _currentSessionId ?? 'unverified-session',
      result: AuditResult.success,
      correlationId: 'login-${DateTime.now().microsecondsSinceEpoch}',
      ipAddress: _demoDevice.ipAddress,
      deviceInformation:
          '${_demoDevice.browser} on ${_demoDevice.operatingSystem}',
    );
    return record.account;
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
    final normalizedEmail = email.trim().toLowerCase();
    if (_accounts.containsKey(normalizedEmail)) {
      throw const AuthFailure('An account already exists for this email.');
    }
    final passwordFailure = PasswordPolicy.validate(password);
    if (passwordFailure != null) throw AuthFailure(passwordFailure);
    final account = UserAccount(
      id: 'user-${_accounts.length + 1}',
      fullName: fullName.trim(),
      email: normalizedEmail,
      role: role,
      status: AccountStatus.pendingVerification,
      emailVerified: false,
    );
    _accounts[normalizedEmail] = (account: account, password: password);
    _currentUser = account;
    return account;
  }

  @override
  Future<UserAccount> createManagedAccount({
    required String fullName,
    required String email,
    required String temporaryPassword,
    required UserRole role,
  }) async {
    final administrator = _currentUser;
    if (administrator == null ||
        !AccessControlPolicy.allows(
          administrator.role,
          Permission.manageUsers,
        )) {
      throw const AuthFailure(
        'An authorized administrator must create managed accounts.',
      );
    }
    if (role == UserRole.applicant) {
      throw const AuthFailure(
        'Applicants must create and verify their own accounts.',
      );
    }
    final normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail.contains('@')) {
      throw const AuthFailure('Enter a valid email address.');
    }
    if (_accounts.containsKey(normalizedEmail)) {
      throw const AuthFailure('An account already exists for this email.');
    }
    final passwordFailure = PasswordPolicy.validate(temporaryPassword);
    if (passwordFailure != null) throw AuthFailure(passwordFailure);

    final account = UserAccount(
      id: 'managed-user-${DateTime.now().microsecondsSinceEpoch}',
      fullName: fullName.trim(),
      email: normalizedEmail,
      role: role,
      status: AccountStatus.active,
      emailVerified: true,
      twoFactorEnabled: AccessControlPolicy.requiresStrongAuthentication(role),
    );
    _accounts[normalizedEmail] = (
      account: account,
      password: temporaryPassword,
    );
    await auditRepository?.append(
      actorId: administrator.id,
      actorRole: administrator.role.name,
      action: AuditAction.roleChanged,
      entityType: 'account',
      entityId: account.id,
      newValue: 'role=${account.role.name},status=${account.status.name}',
      result: AuditResult.success,
      correlationId: 'account-${DateTime.now().microsecondsSinceEpoch}',
    );
    return account;
  }

  @override
  Future<UserAccount> signInWithGoogle() async {
    const account = UserAccount(
      id: 'google-applicant',
      fullName: 'Google Applicant',
      email: 'google.applicant@scholarsphere.local',
      role: UserRole.applicant,
      status: AccountStatus.active,
      emailVerified: true,
    );
    _accounts[account.email] = (account: account, password: '');
    final session = await securityRepository.createSession(
      userId: account.id,
      device: _demoDevice,
      strongAuthentication: true,
      privileged: false,
    );
    _currentSessionId = session.id;
    await securityRepository.recordLogin(
      email: account.email,
      outcome: LoginOutcome.success,
      device: _demoDevice,
      userId: account.id,
    );
    _currentUser = account;
    return account;
  }

  @override
  Future<void> sendPasswordReset(String email) async {
    if (!_accounts.containsKey(email.trim().toLowerCase())) {
      return;
    }
  }

  @override
  Future<void> sendEmailVerification() async {
    if (_currentUser == null) {
      throw const AuthFailure('No account is awaiting verification.');
    }
  }

  @override
  Future<UserAccount> confirmEmailVerification() async {
    final account = _currentUser;
    if (account == null) {
      throw const AuthFailure('No registration is awaiting verification.');
    }
    final verified = UserAccount(
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
    final record = _accounts[account.email];
    if (record != null) {
      _accounts[account.email] = (account: verified, password: record.password);
    }
    final session = await securityRepository.createSession(
      userId: verified.id,
      device: _demoDevice,
      strongAuthentication: verified.twoFactorEnabled,
      privileged: AccessControlPolicy.requiresStrongAuthentication(
        verified.role,
      ),
    );
    _currentSessionId = session.id;
    await securityRepository.recordLogin(
      email: verified.email,
      outcome: LoginOutcome.success,
      device: _demoDevice,
      userId: verified.id,
    );
    _currentUser = verified;
    return verified;
  }

  @override
  Future<void> signOut() async {
    final account = _currentUser;
    final sessionId = _currentSessionId;
    if (sessionId != null) await securityRepository.revokeSession(sessionId);
    if (account != null) {
      await auditRepository?.append(
        actorId: account.id,
        actorRole: account.role.name,
        action: AuditAction.logout,
        entityType: 'session',
        entityId: sessionId ?? 'current-session',
        result: AuditResult.success,
        correlationId: 'logout-${DateTime.now().microsecondsSinceEpoch}',
      );
    }
    _currentSessionId = null;
    _currentUser = null;
  }

  @override
  Future<List<UserAccount>> getAllForAdministration() async =>
      _accounts.values.map((record) => record.account).toList();

  @override
  Future<void> suspendAccount(String userId) async {
    for (final entry in _accounts.entries.toList()) {
      final record = entry.value;
      if (record.account.id != userId) continue;
      final account = record.account;
      _accounts[entry.key] = (
        account: UserAccount(
          id: account.id,
          fullName: account.fullName,
          email: account.email,
          role: account.role,
          status: AccountStatus.suspended,
          emailVerified: account.emailVerified,
          twoFactorEnabled: account.twoFactorEnabled,
          marketingEmailsEnabled: account.marketingEmailsEnabled,
          deadlineNotificationsEnabled: account.deadlineNotificationsEnabled,
        ),
        password: record.password,
      );
      await securityRepository.revokeAllSessions(userId);
      if (_currentUser?.id == userId) {
        _currentUser = null;
        _currentSessionId = null;
      }
      return;
    }
    throw const AuthFailure('Account not found.');
  }
}
