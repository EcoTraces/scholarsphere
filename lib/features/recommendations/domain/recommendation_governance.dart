import 'recommendation.dart';

enum RecommendationLabel {
  strongMatch,
  possibleMatch,
  requiresAdditionalInformation,
  deadlineApproaching,
  fullyFunded,
  noApplicationFee,
  recommendedForCountry,
  recommendedForQualification,
  newlyVerified,
  sponsoredOpportunity,
}

enum RecommendationFeedbackType {
  helpful,
  notRelevant,
  inappropriate,
  dismissed,
}

class PersonalizationControls {
  const PersonalizationControls({
    this.behaviouralRecommendationsEnabled = true,
    this.preferredCountries = const [],
    this.opportunityCategories = const {},
    this.hiddenOpportunityIds = const {},
  });

  final bool behaviouralRecommendationsEnabled;
  final List<String> preferredCountries;
  final Set<RecommendationCategory> opportunityCategories;
  final Set<String> hiddenOpportunityIds;

  PersonalizationControls copyWith({
    bool? behaviouralRecommendationsEnabled,
    List<String>? preferredCountries,
    Set<RecommendationCategory>? opportunityCategories,
    Set<String>? hiddenOpportunityIds,
  }) => PersonalizationControls(
    behaviouralRecommendationsEnabled:
        behaviouralRecommendationsEnabled ??
        this.behaviouralRecommendationsEnabled,
    preferredCountries: preferredCountries ?? this.preferredCountries,
    opportunityCategories: opportunityCategories ?? this.opportunityCategories,
    hiddenOpportunityIds: hiddenOpportunityIds ?? this.hiddenOpportunityIds,
  );
}

class GovernedRecommendation {
  const GovernedRecommendation({
    required this.recommendation,
    required this.labels,
    required this.explanation,
    required this.generatedAt,
    required this.isSponsored,
  });

  final Recommendation recommendation;
  final Set<RecommendationLabel> labels;
  final List<String> explanation;
  final DateTime generatedAt;
  final bool isSponsored;
}

class RecommendationHistoryEntry {
  const RecommendationHistoryEntry({
    required this.userId,
    required this.opportunityId,
    required this.score,
    required this.labels,
    required this.generatedAt,
    required this.hostCountry,
  });
  final String userId;
  final String opportunityId;
  final int score;
  final Set<RecommendationLabel> labels;
  final DateTime generatedAt;
  final String hostCountry;
}

class RecommendationFeedback {
  const RecommendationFeedback({
    required this.userId,
    required this.opportunityId,
    required this.type,
    required this.createdAt,
    this.comment,
  });
  final String userId;
  final String opportunityId;
  final RecommendationFeedbackType type;
  final DateTime createdAt;
  final String? comment;
}

class RecommendationQualityReport {
  const RecommendationQualityReport({
    required this.generatedCount,
    required this.dismissalRate,
    required this.helpfulRate,
    required this.countryDiversity,
    required this.sponsoredShare,
    required this.inappropriateReports,
  });
  final int generatedCount;
  final double dismissalRate;
  final double helpfulRate;
  final int countryDiversity;
  final double sponsoredShare;
  final int inappropriateReports;
}
