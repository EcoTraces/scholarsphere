import '../../opportunities/domain/opportunity.dart';
import 'document_readiness.dart';

class DocumentReadinessService {
  const DocumentReadinessService();

  DocumentReadiness evaluate(
    Opportunity opportunity,
    Iterable<UserDocument> documents,
  ) {
    final required = opportunity.requiredDocuments
        .map(DocumentTypes.fromRequirement)
        .whereType<DocumentType>()
        .toSet();
    final available = documents.map((item) => item.type).toSet();
    return DocumentReadiness(
      required: required,
      available: available,
      missing: required.difference(available),
    );
  }
}
