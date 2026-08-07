class MobileReleasePolicy {
  const MobileReleasePolicy({
    required this.platform,
    required this.minimumVersion,
    required this.latestVersion,
    required this.forceCriticalUpdate,
  });
  final String platform;
  final int minimumVersion;
  final int latestVersion;
  final bool forceCriticalUpdate;

  bool requiresUpdate(int build) =>
      forceCriticalUpdate && build < minimumVersion;
}

class MobileDevice {
  const MobileDevice({
    required this.id,
    required this.userId,
    required this.platform,
    required this.pushToken,
    required this.biometricEnabled,
    required this.lowDataMode,
    required this.lastSyncAt,
  });
  final String id;
  final String userId;
  final String platform;
  final String pushToken;
  final bool biometricEnabled;
  final bool lowDataMode;
  final DateTime lastSyncAt;
}

abstract interface class MobileManagementRepository {
  Future<void> registerDevice(MobileDevice device);
  Future<void> revokeToken(String deviceId);
  Future<bool> requiresUpdate(String platform, int build);
  Future<List<MobileDevice>> devicesFor(String userId);
}

class PublicPageMetadata {
  const PublicPageMetadata({
    required this.path,
    required this.title,
    required this.description,
    required this.canonicalUrl,
    required this.indexable,
  });
  final String path;
  final String title;
  final String description;
  final String canonicalUrl;
  final bool indexable;
}

abstract interface class PublicPortalRepository {
  Future<void> publish(PublicPageMetadata page);
  Future<PublicPageMetadata?> page(String path);
  Future<String> sitemap();
}
