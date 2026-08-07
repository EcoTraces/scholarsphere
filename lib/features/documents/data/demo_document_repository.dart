import '../domain/document_readiness.dart';
import '../domain/document_repository.dart';
import '../../privacy/domain/privacy_models.dart';
import '../../privacy/domain/privacy_repository.dart';

class DemoDocumentRepository implements DocumentRepository {
  DemoDocumentRepository({PrivacyRepository? privacyRepository})
    : _privacyRepository = privacyRepository;

  final PrivacyRepository? _privacyRepository;
  final Map<String, List<UserDocument>> _documents = {};

  @override
  Future<List<UserDocument>> getForUser(String userId) async => [
    ...?_documents[userId],
  ];

  @override
  Future<void> add(UserDocument document) async {
    if (!document.encryptedAtRest) {
      throw ArgumentError('Documents must be encrypted at rest.');
    }
    final records = _documents.putIfAbsent(document.ownerUserId, () => []);
    records.removeWhere((item) => item.type == document.type);
    records.add(document);
  }

  @override
  Future<void> remove(String userId, String documentId) async {
    _documents[userId]?.removeWhere((item) => item.id == documentId);
  }

  @override
  Future<void> grantProviderAccess({
    required String userId,
    required String documentId,
    required String providerId,
  }) async {
    final privacy = _privacyRepository;
    if (privacy != null) {
      final consents = await privacy.getConsents(userId);
      final authorized = consents.any(
        (record) =>
            record.type == ConsentType.thirdPartySharing && record.isActive,
      );
      if (!authorized) {
        throw const PrivacyFailure(
          'Provider access requires active third-party sharing consent.',
        );
      }
    }
    final records = _documents[userId];
    if (records == null) throw StateError('Document not found.');
    final index = records.indexWhere((item) => item.id == documentId);
    if (index == -1) throw StateError('Document not found.');
    records[index] = records[index].withProviderConsent(providerId);
  }
}
