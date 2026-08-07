enum TaxonomyType {
  country,
  region,
  continent,
  nationality,
  institution,
  organization,
  degreeLevel,
  academicField,
  opportunityType,
  fundingType,
  language,
  currency,
  qualification,
  industrySector,
}

class TaxonomyTerm {
  const TaxonomyTerm({
    required this.id,
    required this.type,
    required this.canonicalName,
    required this.code,
    required this.synonyms,
    required this.parentId,
    required this.active,
    required this.version,
    required this.createdAt,
    required this.updatedAt,
  });
  final String id;
  final TaxonomyType type;
  final String canonicalName;
  final String? code;
  final Set<String> synonyms;
  final String? parentId;
  final bool active;
  final int version;
  final DateTime createdAt;
  final DateTime updatedAt;

  TaxonomyTerm copyWith({
    String? canonicalName,
    String? code,
    Set<String>? synonyms,
    String? parentId,
    bool? active,
    int? version,
    DateTime? updatedAt,
  }) => TaxonomyTerm(
    id: id,
    type: type,
    canonicalName: canonicalName ?? this.canonicalName,
    code: code ?? this.code,
    synonyms: synonyms ?? this.synonyms,
    parentId: parentId ?? this.parentId,
    active: active ?? this.active,
    version: version ?? this.version,
    createdAt: createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
  );
}

class TaxonomyVersion {
  const TaxonomyVersion({
    required this.version,
    required this.createdAt,
    required this.createdBy,
    required this.reason,
    required this.termCount,
  });
  final int version;
  final DateTime createdAt;
  final String createdBy;
  final String reason;
  final int termCount;
}
