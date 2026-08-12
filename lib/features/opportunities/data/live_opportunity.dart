/// Data model for opportunities served by the live ScholarSphere backend
/// (scholarsphere_backend/), which collects real records from Grants.gov,
/// Simpler.Grants.gov and the EU Funding & Tenders portal.
///
/// This is intentionally a separate model from [Opportunity] rather than a
/// forced fit into it: the backend sources are institutional/organizational
/// funding calls, not individual scholarships, and do not publish most of
/// the structured fields [Opportunity] expects (eligible nationalities,
/// study levels, required documents, and so on). Representing that
/// honestly as a distinct, leaner model avoids inventing values [Opportunity]
/// would otherwise require.
library;

enum DeadlinePriority {
  unknown,
  normal,
  upcoming,
  important,
  urgent,
  critical,
  lastChance,
  expired;

  static DeadlinePriority fromApi(String value) => switch (value) {
    'NORMAL' => DeadlinePriority.normal,
    'UPCOMING' => DeadlinePriority.upcoming,
    'IMPORTANT' => DeadlinePriority.important,
    'URGENT' => DeadlinePriority.urgent,
    'CRITICAL' => DeadlinePriority.critical,
    'LAST_CHANCE' => DeadlinePriority.lastChance,
    'EXPIRED' => DeadlinePriority.expired,
    _ => DeadlinePriority.unknown,
  };

  String get label => switch (this) {
    DeadlinePriority.unknown => 'Deadline unknown',
    DeadlinePriority.normal => 'Normal',
    DeadlinePriority.upcoming => 'Upcoming',
    DeadlinePriority.important => 'Important',
    DeadlinePriority.urgent => 'Urgent',
    DeadlinePriority.critical => 'Critical',
    DeadlinePriority.lastChance => 'Last chance',
    DeadlinePriority.expired => 'Expired',
  };
}

class LiveOpportunity {
  const LiveOpportunity({
    required this.id,
    required this.title,
    required this.opportunityType,
    required this.providerName,
    required this.country,
    required this.description,
    required this.openingDate,
    required this.deadline,
    required this.opportunityStatus,
    required this.fundingType,
    required this.awardFloor,
    required this.awardCeiling,
    required this.currency,
    required this.officialSourceUrl,
    required this.officialApplicationUrl,
    required this.verificationStatus,
    required this.sourceCode,
    required this.sourceName,
    required this.sourceTrustLevel,
    required this.collectedAt,
    required this.lastExternalUpdateAt,
    required this.verifiedAt,
    required this.daysRemaining,
    required this.deadlinePriority,
  });

  factory LiveOpportunity.fromJson(Map<String, dynamic> json) =>
      LiveOpportunity(
        id: json['id'] as String,
        title: json['title'] as String,
        opportunityType: json['opportunity_type'] as String,
        providerName: json['provider_name'] as String,
        country: json['country'] as String?,
        description: json['description'] as String?,
        openingDate: _date(json['opening_date']),
        deadline: _date(json['deadline']),
        opportunityStatus: json['opportunity_status'] as String,
        fundingType: json['funding_type'] as String?,
        awardFloor: (json['award_floor'] as num?)?.toDouble(),
        awardCeiling: (json['award_ceiling'] as num?)?.toDouble(),
        currency: json['currency'] as String?,
        officialSourceUrl: json['official_source_url'] as String?,
        officialApplicationUrl: json['official_application_url'] as String?,
        verificationStatus: json['verification_status'] as String,
        sourceCode: json['source_code'] as String,
        sourceName: json['source_name'] as String,
        sourceTrustLevel: json['source_trust_level'] as String,
        collectedAt: DateTime.parse(json['collected_at'] as String),
        lastExternalUpdateAt: DateTime.parse(
          json['last_external_update_at'] as String,
        ),
        verifiedAt: json['verified_at'] == null
            ? null
            : DateTime.parse(json['verified_at'] as String),
        daysRemaining: json['days_remaining'] as int?,
        deadlinePriority: DeadlinePriority.fromApi(
          json['deadline_priority'] as String,
        ),
      );

  final String id;
  final String title;
  final String opportunityType;
  final String providerName;
  final String? country;
  final String? description;
  final DateTime? openingDate;
  final DateTime? deadline;
  final String opportunityStatus;
  final String? fundingType;
  final double? awardFloor;
  final double? awardCeiling;
  final String? currency;
  final String? officialSourceUrl;
  final String? officialApplicationUrl;
  final String verificationStatus;
  final String sourceCode;
  final String sourceName;
  final String sourceTrustLevel;
  final DateTime collectedAt;
  final DateTime lastExternalUpdateAt;
  final DateTime? verifiedAt;
  final int? daysRemaining;
  final DeadlinePriority deadlinePriority;

  bool get isVerified => verificationStatus == 'verified';

  String get awardRangeLabel {
    if (awardFloor == null && awardCeiling == null) return 'Not specified by source';
    final currencyLabel = currency ?? '';
    if (awardFloor != null && awardCeiling != null && awardFloor != awardCeiling) {
      return '$currencyLabel ${_money(awardFloor!)} - ${_money(awardCeiling!)}';
    }
    final amount = awardCeiling ?? awardFloor!;
    return '$currencyLabel ${_money(amount)}';
  }

  static String _money(double value) {
    final rounded = value.round();
    final text = rounded.toString();
    final buffer = StringBuffer();
    for (var index = 0; index < text.length; index++) {
      if (index > 0 && (text.length - index) % 3 == 0) buffer.write(',');
      buffer.write(text[index]);
    }
    return buffer.toString();
  }

  static DateTime? _date(dynamic value) =>
      value == null ? null : DateTime.parse(value as String);
}

class LiveOpportunityPage {
  const LiveOpportunityPage({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  factory LiveOpportunityPage.fromJson(Map<String, dynamic> json) =>
      LiveOpportunityPage(
        items: (json['items'] as List<dynamic>)
            .map((item) => LiveOpportunity.fromJson(item as Map<String, dynamic>))
            .toList(),
        total: json['total'] as int,
        page: json['page'] as int,
        pageSize: json['page_size'] as int,
      );

  final List<LiveOpportunity> items;
  final int total;
  final int page;
  final int pageSize;
}

class FieldEvidence {
  const FieldEvidence({
    required this.field,
    required this.value,
    required this.confidence,
  });

  factory FieldEvidence.fromJson(Map<String, dynamic> json) => FieldEvidence(
    field: json['field'] as String,
    value: json['value'],
    confidence: json['confidence'] as String,
  );

  final String field;
  final dynamic value;
  final String confidence;
}

class LiveOpportunityEvidence {
  const LiveOpportunityEvidence({
    required this.opportunityId,
    required this.sourceCode,
    required this.sourceName,
    required this.sourceType,
    required this.sourceTrustLevel,
    required this.officialSourceUrl,
    required this.collectedAt,
    required this.fieldEvidence,
    required this.rawPayload,
  });

  factory LiveOpportunityEvidence.fromJson(Map<String, dynamic> json) =>
      LiveOpportunityEvidence(
        opportunityId: json['opportunity_id'] as String,
        sourceCode: json['source_code'] as String,
        sourceName: json['source_name'] as String,
        sourceType: json['source_type'] as String,
        sourceTrustLevel: json['source_trust_level'] as String,
        officialSourceUrl: json['official_source_url'] as String?,
        collectedAt: DateTime.parse(json['collected_at'] as String),
        fieldEvidence: (json['field_evidence'] as List<dynamic>)
            .map((item) => FieldEvidence.fromJson(item as Map<String, dynamic>))
            .toList(),
        rawPayload: json['raw_payload'] as Map<String, dynamic>,
      );

  final String opportunityId;
  final String sourceCode;
  final String sourceName;
  final String sourceType;
  final String sourceTrustLevel;
  final String? officialSourceUrl;
  final DateTime collectedAt;
  final List<FieldEvidence> fieldEvidence;
  final Map<String, dynamic> rawPayload;
}

class VerificationHistoryItem {
  const VerificationHistoryItem({
    required this.previousStatus,
    required this.newStatus,
    required this.reason,
    required this.changedAt,
  });

  factory VerificationHistoryItem.fromJson(Map<String, dynamic> json) =>
      VerificationHistoryItem(
        previousStatus: json['previous_status'] as String,
        newStatus: json['new_status'] as String,
        reason: json['reason'] as String,
        changedAt: DateTime.parse(json['changed_at'] as String),
      );

  final String previousStatus;
  final String newStatus;
  final String reason;
  final DateTime changedAt;
}
