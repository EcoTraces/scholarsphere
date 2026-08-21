from app.models.applicant_document import DocumentType


def document_type_from_requirement(value: str) -> DocumentType | None:
    """Port of lib/features/documents/domain/document_readiness.dart's

    DocumentTypes.fromRequirement - keep the two in sync.
    """
    normalized = value.lower()
    if "passport" in normalized:
        return DocumentType.passport
    if "curriculum vitae" in normalized or normalized == "cv" or "resume" in normalized:
        return DocumentType.curriculum_vitae
    if "transcript" in normalized:
        return DocumentType.academic_transcript
    if "degree certificate" in normalized:
        return DocumentType.degree_certificate
    if "recommendation" in normalized:
        return DocumentType.recommendation_letters
    if "motivation" in normalized:
        return DocumentType.motivation_letter
    if "personal statement" in normalized:
        return DocumentType.personal_statement
    if "research proposal" in normalized:
        return DocumentType.research_proposal
    if "english" in normalized and "certificate" in normalized:
        return DocumentType.english_language_certificate
    if "work" in normalized and "letter" in normalized:
        return DocumentType.work_experience_letter
    if "birth certificate" in normalized:
        return DocumentType.birth_certificate
    if "portfolio" in normalized:
        return DocumentType.portfolio
    if "financial" in normalized:
        return DocumentType.financial_documents
    return None
