import '../../matching/domain/eligibility_matcher.dart';
import '../../opportunities/domain/opportunity.dart';
import '../../profiles/domain/applicant_profile.dart';
import 'recommendation.dart';

class RecommendationEngine {
  const RecommendationEngine({this.matcher = const EligibilityMatcher()});

  final EligibilityMatcher matcher;

  List<Recommendation> recommend({
    required Iterable<Opportunity> opportunities,
    required ApplicantProfile profile,
    required RecommendationCategory category,
    RecommendationSignals signals = const RecommendationSignals(),
    DateTime? now,
  }) {
    final today = now ?? DateTime.now();
    final ranked =
        opportunities
            .where((item) => _belongs(item, profile, category, today))
            .map((item) => _rank(item, profile, signals, today))
            .toList()
          ..sort((left, right) => right.score.compareTo(left.score));
    return ranked;
  }

  bool _belongs(
    Opportunity item,
    ApplicantProfile profile,
    RecommendationCategory category,
    DateTime now,
  ) => switch (category) {
    RecommendationCategory.bestMatches => true,
    RecommendationCategory.newlyPublished => item.applicationOpenDate.isAfter(
      now.subtract(const Duration(days: 45)),
    ),
    RecommendationCategory.fullyFunded =>
      item.funding == FundingType.fullyFunded,
    RecommendationCategory.noApplicationFee => item.applicationFee == 0,
    RecommendationCategory.closingSoon =>
      item.deadline.isAfter(now) &&
          !item.deadline.isAfter(now.add(const Duration(days: 30))),
    RecommendationCategory.suitableForCountry =>
      profile.nationality.isNotEmpty &&
          (item.eligibleNationalities.any(
                (value) => value.toLowerCase() == 'all nationalities',
              ) ||
              _overlap(item.eligibleNationalities, [profile.nationality])),
    RecommendationCategory.suitableForDegree => _overlap(item.fieldsOfStudy, [
      profile.degreeField,
      ...profile.areasOfInterest,
    ]),
    RecommendationCategory.online =>
      item.deliveryFormat == DeliveryFormat.online,
    RecommendationCategory.noIelts => !item.languageRequirements.any(
      (value) => value.toLowerCase().contains('ielts'),
    ),
    RecommendationCategory.undergraduate => _hasLevel(item, 'undergraduate'),
    RecommendationCategory.masters =>
      _hasLevel(item, 'master') || _hasLevel(item, 'graduate'),
    RecommendationCategory.phd => _hasLevel(item, 'phd'),
    RecommendationCategory.professional => _hasLevel(item, 'professional'),
  };

  Recommendation _rank(
    Opportunity item,
    ApplicantProfile profile,
    RecommendationSignals signals,
    DateTime now,
  ) {
    final match = matcher.evaluate(profile, item);
    var score = match.score;
    final reasons = <String>['${match.score}% eligibility match'];
    if (profile.preferredCountries.any(
      (country) => country.toLowerCase() == item.hostCountry.toLowerCase(),
    )) {
      score += 8;
      reasons.add('Preferred destination');
    }
    if (signals.savedOpportunityIds.contains(item.id)) {
      score += 4;
      reasons.add('Similar to saved interests');
    }
    if (signals.appliedOpportunityIds.contains(item.id)) {
      score -= 20;
    }
    if (signals.previousSearches.any(
      (query) =>
          item.title.toLowerCase().contains(query.toLowerCase()) ||
          item.fieldsOfStudy.any(
            (field) => field.toLowerCase().contains(query.toLowerCase()),
          ),
    )) {
      score += 5;
      reasons.add('Related to previous searches');
    }
    final days = item.deadline.difference(now).inDays;
    if (days >= 0 && days <= 30) {
      score += 3;
      reasons.add('Deadline approaching');
    }
    return Recommendation(
      opportunity: item,
      score: score.clamp(0, 100).toInt(),
      reasons: reasons,
    );
  }

  bool _hasLevel(Opportunity item, String value) =>
      item.studyLevels.any((level) => level.toLowerCase().contains(value));

  bool _overlap(List<String> left, List<String> right) => left.any(
    (value) => right.any(
      (other) =>
          other.isNotEmpty &&
          (value.toLowerCase().contains(other.toLowerCase()) ||
              other.toLowerCase().contains(value.toLowerCase())),
    ),
  );
}
