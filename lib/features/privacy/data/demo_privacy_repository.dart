import '../domain/privacy_models.dart';
import '../domain/privacy_repository.dart';
import '../domain/privacy_rules.dart';

class DemoPrivacyRepository implements PrivacyRepository {
  DemoPrivacyRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DateTime Function() _clock;
  final Map<String, Map<ConsentType, ConsentRecord>> _consents = {};
  final List<PrivacyRequest> _requests = [];
  final List<OrganizationAccessRecord> _access = [];
  final List<PrivacyIncident> _incidents = [];
  final Set<String> _minorUsers = {};

  @override
  Future<void> setMinorStatus(String userId, bool isMinor) async {
    isMinor ? _minorUsers.add(userId) : _minorUsers.remove(userId);
  }

  @override
  Future<List<ConsentRecord>> getConsents(String userId) async =>
      _consents[userId]?.values.toList() ?? [];

  @override
  Future<void> grantConsent({
    required String userId,
    required ConsentType type,
    required String policyVersion,
  }) async {
    if (_minorUsers.contains(userId) && !PrivacyRules.minorCanGrant(type)) {
      throw const PrivacyFailure(
        'This consent is restricted for minor accounts.',
      );
    }
    _consents.putIfAbsent(userId, () => {})[type] = ConsentRecord(
      userId: userId,
      type: type,
      policyVersion: policyVersion,
      grantedAt: _clock(),
      withdrawnAt: null,
    );
  }

  @override
  Future<void> withdrawConsent(String userId, ConsentType type) async {
    if ({
      ConsentType.privacyPolicy,
      ConsentType.termsAndConditions,
    }.contains(type)) {
      throw const PrivacyFailure(
        'Required legal acceptance cannot be withdrawn while the account '
        'remains active. Submit an account-deletion request instead.',
      );
    }
    final record = _consents[userId]?[type];
    if (record != null) _consents[userId]![type] = record.withdraw(_clock());
  }

  @override
  Future<PrivacyRequest> submitRequest({
    required String userId,
    required PrivacyRequestType type,
    String notes = '',
  }) async {
    final request = PrivacyRequest(
      id: 'privacy-${_clock().microsecondsSinceEpoch}-${_requests.length}',
      userId: userId,
      type: type,
      status: PrivacyRequestStatus.submitted,
      submittedAt: _clock(),
      completedAt: null,
      notes: notes,
    );
    _requests.add(request);
    return request;
  }

  @override
  Future<List<PrivacyRequest>> getRequests(String userId) async =>
      _requests.where((item) => item.userId == userId).toList();

  @override
  Future<List<OrganizationAccessRecord>> getAccessHistory(
    String userId,
  ) async => _access.where((item) => item.userId == userId).toList();

  @override
  Future<void> recordOrganizationAccess({
    required String userId,
    required String organizationId,
    required String organizationName,
    required Set<String> dataCategories,
  }) async {
    final consent = _consents[userId]?[ConsentType.thirdPartySharing];
    if (consent == null || !consent.isActive) {
      throw const PrivacyFailure(
        'Third-party access requires explicit active user consent.',
      );
    }
    _access.add(
      OrganizationAccessRecord(
        id: 'access-${_clock().microsecondsSinceEpoch}-${_access.length}',
        userId: userId,
        organizationId: organizationId,
        organizationName: organizationName,
        dataCategories: dataCategories,
        accessedAt: _clock(),
        consentRecordType: ConsentType.thirdPartySharing,
      ),
    );
  }

  @override
  Future<void> recordIncident(PrivacyIncident incident) async {
    _incidents.add(incident);
  }

  @override
  Future<List<PrivacyIncident>> getIncidentsForAdministration() async => [
    ..._incidents,
  ];
}
