import '../domain/provider_profile.dart';
import '../domain/provider_repository.dart';

class DemoProviderRepository implements ProviderRepository {
  DemoProviderRepository({DateTime Function()? clock})
    : _clock = clock ?? DateTime.now {
    final now = _clock();
    _profiles['demo-provider-organization'] = ProviderProfile(
      id: 'demo-provider-organization',
      ownerUserId: 'demo-provider',
      organizationName: 'Global Education Foundation',
      organizationType: 'Foundation',
      registrationNumber: 'GEF-2026-001',
      country: 'Global',
      officialWebsite: 'https://education.example',
      officialEmailDomain: 'education.example',
      physicalAddress: 'International Programs Office',
      contactPerson: 'Provider Administrator',
      contactPhone: '+000000000',
      supportingDocuments: const ['registration-certificate.pdf'],
      socialMediaLinks: const [],
      status: ProviderStatus.verified,
      riskScore: 0,
      permissions: const {
        ProviderPermission.manageOrganization,
        ProviderPermission.publishOpportunities,
        ProviderPermission.manageAdmins,
      },
      verificationDate: now,
      verifiedBy: 'system-fixture',
      reverificationDate: now.add(const Duration(days: 365)),
    );
  }

  final DateTime Function() _clock;
  final Map<String, ProviderProfile> _profiles = {};

  @override
  Future<ProviderProfile?> getForUser(String userId) async {
    final matches = _profiles.values.where((p) => p.ownerUserId == userId);
    return matches.isEmpty ? null : matches.first;
  }

  @override
  Future<List<ProviderProfile>> getReviewQueue() async => _profiles.values
      .where(
        (p) => {
          ProviderStatus.pendingReview,
          ProviderStatus.additionalInformationRequired,
          ProviderStatus.verificationExpired,
        }.contains(p.status),
      )
      .toList();

  @override
  Future<ProviderProfile> register(ProviderProfile profile) async {
    if (_profiles.values.any(
      (p) =>
          p.officialEmailDomain.toLowerCase() ==
          profile.officialEmailDomain.toLowerCase(),
    )) {
      throw const ProviderFailure(
        'This organization domain is already registered.',
      );
    }
    final score = _riskScore(profile);
    final saved = profile.copyWith(
      status: ProviderStatus.pendingReview,
      riskScore: score,
      permissions: const {ProviderPermission.manageOrganization},
    );
    _profiles[saved.id] = saved;
    return saved;
  }

  @override
  Future<ProviderProfile> review({
    required String providerId,
    required String officerId,
    required ProviderStatus decision,
    required ProviderReviewChecklist checklist,
    String? note,
  }) async {
    final current = _require(providerId);
    if (decision == ProviderStatus.verified && !checklist.complete) {
      throw const ProviderFailure(
        'Every verification check must pass before approval.',
      );
    }
    final now = _clock();
    final updated = current.copyWith(
      status: decision,
      permissions: decision == ProviderStatus.verified
          ? const {
              ProviderPermission.manageOrganization,
              ProviderPermission.publishOpportunities,
              ProviderPermission.manageAdmins,
            }
          : const {ProviderPermission.manageOrganization},
      verificationDate: decision == ProviderStatus.verified ? now : null,
      verifiedBy: decision == ProviderStatus.verified ? officerId : null,
      reverificationDate: decision == ProviderStatus.verified
          ? now.add(const Duration(days: 365))
          : null,
      reviewNote: note,
    );
    _profiles[providerId] = updated;
    return updated;
  }

  @override
  Future<ProviderProfile> suspend(String providerId, String reason) async {
    final updated = _require(providerId).copyWith(
      status: ProviderStatus.suspended,
      permissions: const {},
      reviewNote: reason,
    );
    _profiles[providerId] = updated;
    return updated;
  }

  @override
  Future<ProviderProfile> appeal(String providerId, String reason) async {
    final current = _require(providerId);
    if (current.status != ProviderStatus.rejected &&
        current.status != ProviderStatus.suspended) {
      throw const ProviderFailure(
        'Only rejected or suspended providers can appeal.',
      );
    }
    final updated = current.copyWith(
      status: ProviderStatus.pendingReview,
      reviewNote: 'Appeal: $reason',
      appeals: [
        ...current.appeals,
        ProviderAppeal(
          reason: reason,
          submittedAt: _clock(),
          status: 'Pending',
        ),
      ],
    );
    _profiles[providerId] = updated;
    return updated;
  }

  @override
  Future<ProviderProfile> addAdministrator(
    String providerId,
    ProviderAdministrator administrator,
  ) async {
    final current = _require(providerId);
    if (!current.hasVerifiedBadge) {
      throw const ProviderFailure(
        'Only verified providers can add administrators.',
      );
    }
    final updated = current.copyWith(
      administrators: [...current.administrators, administrator],
      activityHistory: [
        ...current.activityHistory,
        ProviderActivity(
          action: 'Administrator added',
          actorId: current.ownerUserId,
          occurredAt: _clock(),
        ),
      ],
    );
    _profiles[providerId] = updated;
    return updated;
  }

  @override
  Future<bool> canPublish(String userId) async {
    final profile = await getForUser(userId);
    return profile != null &&
        profile.hasVerifiedBadge &&
        profile.permissions.contains(ProviderPermission.publishOpportunities);
  }

  ProviderProfile _require(String id) {
    final value = _profiles[id];
    if (value == null) throw const ProviderFailure('Provider was not found.');
    return value;
  }

  int _riskScore(ProviderProfile profile) {
    var score = 0;
    final domain = profile.officialEmailDomain.toLowerCase().trim();
    if ({'gmail.com', 'yahoo.com', 'outlook.com'}.contains(domain)) score += 55;
    final websiteHost =
        Uri.tryParse(profile.officialWebsite)?.host.toLowerCase() ?? '';
    if (websiteHost.isEmpty || !websiteHost.endsWith(domain)) score += 25;
    if (profile.registrationNumber.trim().isEmpty) score += 15;
    if (profile.supportingDocuments.isEmpty) score += 15;
    return score.clamp(0, 100).toInt();
  }
}
