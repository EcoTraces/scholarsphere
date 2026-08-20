enum DocumentType {
  passport,
  curriculumVitae,
  academicTranscript,
  degreeCertificate,
  recommendationLetters,
  motivationLetter,
  personalStatement,
  researchProposal,
  englishLanguageCertificate,
  workExperienceLetter,
  birthCertificate,
  portfolio,
  financialDocuments,
}

class UserDocument {
  const UserDocument({
    required this.id,
    required this.ownerUserId,
    required this.type,
    required this.fileName,
    required this.uploadedAt,
    required this.encryptedAtRest,
    this.sharedWithProviderIds = const {},
    this.storagePath,
  });

  final String id;
  final String ownerUserId;
  final DocumentType type;
  final String fileName;
  final DateTime uploadedAt;
  final bool encryptedAtRest;
  final Set<String> sharedWithProviderIds;

  /// The real Firebase Storage location for this file
  /// (`applicant-documents/{uid}/{fileName}`), set only when this record
  /// backs an actual uploaded file. Null for records with no real file
  /// behind them (e.g. constructed by a demo/in-memory repository).
  final String? storagePath;

  bool canProviderAccess(String providerId) =>
      sharedWithProviderIds.contains(providerId);

  UserDocument withProviderConsent(String providerId) => UserDocument(
    id: id,
    ownerUserId: ownerUserId,
    type: type,
    fileName: fileName,
    uploadedAt: uploadedAt,
    encryptedAtRest: encryptedAtRest,
    sharedWithProviderIds: {...sharedWithProviderIds, providerId},
    storagePath: storagePath,
  );
}

class DocumentReadiness {
  const DocumentReadiness({
    required this.required,
    required this.available,
    required this.missing,
  });

  final Set<DocumentType> required;
  final Set<DocumentType> available;
  final Set<DocumentType> missing;

  int get readyCount => available.intersection(required).length;
  int get requiredCount => required.length;
}

abstract final class DocumentTypes {
  static DocumentType? fromRequirement(String value) {
    final normalized = value.toLowerCase();
    if (normalized.contains('passport')) return DocumentType.passport;
    if (normalized.contains('curriculum vitae') ||
        normalized == 'cv' ||
        normalized.contains('resume')) {
      return DocumentType.curriculumVitae;
    }
    if (normalized.contains('transcript')) {
      return DocumentType.academicTranscript;
    }
    if (normalized.contains('degree certificate')) {
      return DocumentType.degreeCertificate;
    }
    if (normalized.contains('recommendation')) {
      return DocumentType.recommendationLetters;
    }
    if (normalized.contains('motivation')) {
      return DocumentType.motivationLetter;
    }
    if (normalized.contains('personal statement')) {
      return DocumentType.personalStatement;
    }
    if (normalized.contains('research proposal')) {
      return DocumentType.researchProposal;
    }
    if (normalized.contains('english') && normalized.contains('certificate')) {
      return DocumentType.englishLanguageCertificate;
    }
    if (normalized.contains('work') && normalized.contains('letter')) {
      return DocumentType.workExperienceLetter;
    }
    if (normalized.contains('birth certificate')) {
      return DocumentType.birthCertificate;
    }
    if (normalized.contains('portfolio')) return DocumentType.portfolio;
    if (normalized.contains('financial')) {
      return DocumentType.financialDocuments;
    }
    return null;
  }

  static String label(DocumentType type) => switch (type) {
    DocumentType.passport => 'Passport',
    DocumentType.curriculumVitae => 'Curriculum vitae',
    DocumentType.academicTranscript => 'Academic transcript',
    DocumentType.degreeCertificate => 'Degree certificate',
    DocumentType.recommendationLetters => 'Recommendation letters',
    DocumentType.motivationLetter => 'Motivation letter',
    DocumentType.personalStatement => 'Personal statement',
    DocumentType.researchProposal => 'Research proposal',
    DocumentType.englishLanguageCertificate => 'English-language certificate',
    DocumentType.workExperienceLetter => 'Work-experience letter',
    DocumentType.birthCertificate => 'Birth certificate',
    DocumentType.portfolio => 'Portfolio',
    DocumentType.financialDocuments => 'Financial documents',
  };
}
