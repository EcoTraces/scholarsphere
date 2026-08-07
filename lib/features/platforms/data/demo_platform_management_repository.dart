import '../domain/platform_management.dart';

class DemoMobileManagementRepository implements MobileManagementRepository {
  DemoMobileManagementRepository(this.policies);
  final List<MobileReleasePolicy> policies;
  final Map<String, MobileDevice> _devices = {};

  @override
  Future<void> registerDevice(MobileDevice device) async {
    _devices[device.id] = device;
  }

  @override
  Future<List<MobileDevice>> devicesFor(String userId) async =>
      _devices.values.where((device) => device.userId == userId).toList();

  @override
  Future<bool> requiresUpdate(String platform, int build) async {
    final matches = policies.where((policy) => policy.platform == platform);
    return matches.isNotEmpty && matches.first.requiresUpdate(build);
  }

  @override
  Future<void> revokeToken(String deviceId) async {
    final device = _devices.remove(deviceId);
    if (device == null) throw StateError('Device not found');
  }
}

class DemoPublicPortalRepository implements PublicPortalRepository {
  final Map<String, PublicPageMetadata> _pages = {};

  @override
  Future<void> publish(PublicPageMetadata page) async {
    if (!page.path.startsWith('/'))
      throw ArgumentError('Public paths must be absolute');
    _pages[page.path] = page;
  }

  @override
  Future<PublicPageMetadata?> page(String path) async => _pages[path];

  @override
  Future<String> sitemap() async {
    final paths = _pages.values
        .where((page) => page.indexable)
        .map((page) => '<url><loc>${page.canonicalUrl}</loc></url>')
        .join();
    return '<?xml version="1.0" encoding="UTF-8"?><urlset>$paths</urlset>';
  }
}
