import '../../opportunities/domain/opportunity.dart';

enum GeographicRegion {
  europe,
  asia,
  northAmerica,
  canada,
  latinAmerica,
  africa,
  middleEast,
  australiaOceania,
  globalOnline,
}

enum DeadlineWindow { any, sevenDays, thirtyDays, ninetyDays }

enum OpportunityAvailability { any, open, closed }

class OpportunityFilter {
  const OpportunityFilter({
    this.query = '',
    this.type,
    this.country,
    this.region,
    this.provider,
    this.field,
    this.studyLevel,
    this.funding,
    this.noApplicationFee = false,
    this.eligibleNationality,
    this.deadlineWindow = DeadlineWindow.any,
    this.deliveryFormat,
    this.applicantAge,
    this.availableWorkExperienceYears,
    this.language,
    this.verifiedOnly = true,
    this.availability = OpportunityAvailability.open,
  });

  final String query;
  final OpportunityType? type;
  final String? country;
  final GeographicRegion? region;
  final String? provider;
  final String? field;
  final String? studyLevel;
  final FundingType? funding;
  final bool noApplicationFee;
  final String? eligibleNationality;
  final DeadlineWindow deadlineWindow;
  final DeliveryFormat? deliveryFormat;
  final int? applicantAge;
  final double? availableWorkExperienceYears;
  final String? language;
  final bool verifiedOnly;
  final OpportunityAvailability availability;

  int get activeCount => [
    type,
    country,
    region,
    provider,
    field,
    studyLevel,
    funding,
    noApplicationFee ? true : null,
    eligibleNationality,
    deadlineWindow == DeadlineWindow.any ? null : deadlineWindow,
    deliveryFormat,
    applicantAge,
    availableWorkExperienceYears,
    language,
    verifiedOnly ? true : null,
    availability == OpportunityAvailability.any ? null : availability,
  ].where((value) => value != null).length;

  OpportunityFilter copyWith({
    String? query,
    OpportunityType? type,
    bool clearType = false,
    String? country,
    GeographicRegion? region,
    String? provider,
    String? field,
    String? studyLevel,
    FundingType? funding,
    bool? noApplicationFee,
    String? eligibleNationality,
    DeadlineWindow? deadlineWindow,
    DeliveryFormat? deliveryFormat,
    int? applicantAge,
    double? availableWorkExperienceYears,
    String? language,
    bool? verifiedOnly,
    OpportunityAvailability? availability,
  }) => OpportunityFilter(
    query: query ?? this.query,
    type: clearType ? null : type ?? this.type,
    country: country ?? this.country,
    region: region ?? this.region,
    provider: provider ?? this.provider,
    field: field ?? this.field,
    studyLevel: studyLevel ?? this.studyLevel,
    funding: funding ?? this.funding,
    noApplicationFee: noApplicationFee ?? this.noApplicationFee,
    eligibleNationality: eligibleNationality ?? this.eligibleNationality,
    deadlineWindow: deadlineWindow ?? this.deadlineWindow,
    deliveryFormat: deliveryFormat ?? this.deliveryFormat,
    applicantAge: applicantAge ?? this.applicantAge,
    availableWorkExperienceYears:
        availableWorkExperienceYears ?? this.availableWorkExperienceYears,
    language: language ?? this.language,
    verifiedOnly: verifiedOnly ?? this.verifiedOnly,
    availability: availability ?? this.availability,
  );
}
