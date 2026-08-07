import 'document_readiness.dart';

abstract interface class DocumentRepository {
  Future<List<UserDocument>> getForUser(String userId);

  Future<void> add(UserDocument document);

  Future<void> remove(String userId, String documentId);

  Future<void> grantProviderAccess({
    required String userId,
    required String documentId,
    required String providerId,
  });
}
