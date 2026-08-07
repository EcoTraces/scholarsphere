import '../../opportunities/domain/opportunity.dart';

enum RecommendationCategory {
  bestMatches,
  newlyPublished,
  fullyFunded,
  noApplicationFee,
  closingSoon,
  suitableForCountry,
  suitableForDegree,
  online,
  noIelts,
  undergraduate,
  masters,
  phd,
  professional,
}

class Recommendation {
  const Recommendation({
    required this.opportunity,
    required this.score,
    required this.reasons,
  });

  final Opportunity opportunity;
  final int score;
  final List<String> reasons;
}

class RecommendationSignals {
  const RecommendationSignals({
    this.previousSearches = const [],
    this.savedOpportunityIds = const {},
    this.appliedOpportunityIds = const {},
  });

  final List<String> previousSearches;
  final Set<String> savedOpportunityIds;
  final Set<String> appliedOpportunityIds;
}
