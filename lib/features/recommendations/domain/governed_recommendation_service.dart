import '../../opportunities/domain/opportunity.dart';
import '../../profiles/domain/applicant_profile.dart';
import 'recommendation.dart';
import 'recommendation_engine.dart';
import 'recommendation_governance.dart';
import 'recommendation_governance_repository.dart';

class GovernedRecommendationService {
  const GovernedRecommendationService({
    required this.repository,
    this.engine = const RecommendationEngine(),
    this.clock,
  });

  final RecommendationGovernanceRepository repository;
  final RecommendationEngine engine;
  final DateTime Function()? clock;

  Future<List<GovernedRecommendation>> recommend({
    required String userId,
    required Iterable<Opportunity> opportunities,
    required ApplicantProfile profile,
    required RecommendationCategory category,
    RecommendationSignals signals = const RecommendationSignals(),
    Set<String> sponsoredOpportunityIds = const {},
    int limit = 20,
  }) async {
    final controls = await repository.getControls(userId);
    if (controls.opportunityCategories.isNotEmpty &&
        !controls.opportunityCategories.contains(category)) {
      return const [];
    }
    final effectiveProfile = controls.preferredCountries.isEmpty
        ? profile
        : _withPreferredCountries(profile, controls.preferredCountries);
    final effectiveSignals = controls.behaviouralRecommendationsEnabled
        ? signals
        : RecommendationSignals(
            savedOpportunityIds: signals.savedOpportunityIds,
            appliedOpportunityIds: signals.appliedOpportunityIds,
          );
    final ranked = engine
        .recommend(
          opportunities: opportunities.where(
            (item) => !controls.hiddenOpportunityIds.contains(item.id),
          ),
          profile: effectiveProfile,
          category: category,
          signals: effectiveSignals,
          now: (clock ?? DateTime.now)(),
        )
        .where(
          (item) =>
              !signals.appliedOpportunityIds.contains(item.opportunity.id),
        )
        .toList();
    final diverse = _diversify(ranked, limit);
    final generatedAt = (clock ?? DateTime.now)();
    final governed = <GovernedRecommendation>[];
    for (final item in diverse) {
      final sponsored = sponsoredOpportunityIds.contains(item.opportunity.id);
      final labels = _labels(item, profile, generatedAt, sponsored);
      final result = GovernedRecommendation(
        recommendation: item,
        labels: labels,
        explanation: [
          ...item.reasons,
          if (!controls.behaviouralRecommendationsEnabled)
            'Behavioural personalization is disabled.',
          if (sponsored) 'This is labeled sponsored content.',
        ],
        generatedAt: generatedAt,
        isSponsored: sponsored,
      );
      governed.add(result);
      await repository.recordHistory(
        RecommendationHistoryEntry(
          userId: userId,
          opportunityId: item.opportunity.id,
          score: item.score,
          labels: labels,
          generatedAt: generatedAt,
          hostCountry: item.opportunity.hostCountry,
        ),
      );
    }
    return governed;
  }

  List<Recommendation> _diversify(List<Recommendation> ranked, int limit) {
    final selected = <Recommendation>[];
    final remaining = [...ranked];
    while (remaining.isNotEmpty && selected.length < limit) {
      final usedCountries = selected
          .map((item) => item.opportunity.hostCountry)
          .toSet();
      final index = remaining.indexWhere(
        (item) => !usedCountries.contains(item.opportunity.hostCountry),
      );
      selected.add(remaining.removeAt(index < 0 ? 0 : index));
    }
    return selected;
  }

  Set<RecommendationLabel> _labels(
    Recommendation item,
    ApplicantProfile profile,
    DateTime now,
    bool sponsored,
  ) {
    final opportunity = item.opportunity;
    return {
      if (item.score >= 85)
        RecommendationLabel.strongMatch
      else if (item.score >= 50)
        RecommendationLabel.possibleMatch
      else
        RecommendationLabel.requiresAdditionalInformation,
      if (opportunity.deadline.isAfter(now) &&
          opportunity.deadline.difference(now).inDays <= 30)
        RecommendationLabel.deadlineApproaching,
      if (opportunity.funding == FundingType.fullyFunded)
        RecommendationLabel.fullyFunded,
      if (opportunity.applicationFee == 0) RecommendationLabel.noApplicationFee,
      if (profile.preferredCountries.any(
        (country) =>
            country.toLowerCase() == opportunity.hostCountry.toLowerCase(),
      ))
        RecommendationLabel.recommendedForCountry,
      if (opportunity.fieldsOfStudy.any(
        (field) =>
            field.toLowerCase().contains(profile.degreeField.toLowerCase()),
      ))
        RecommendationLabel.recommendedForQualification,
      if (opportunity.lastVerifiedAt != null &&
          opportunity.lastVerifiedAt!.isAfter(
            now.subtract(const Duration(days: 30)),
          ))
        RecommendationLabel.newlyVerified,
      if (sponsored) RecommendationLabel.sponsoredOpportunity,
    };
  }

  ApplicantProfile _withPreferredCountries(
    ApplicantProfile profile,
    List<String> countries,
  ) => ApplicantProfile(
    userId: profile.userId,
    fullName: profile.fullName,
    nationality: profile.nationality,
    countryOfResidence: profile.countryOfResidence,
    dateOfBirth: profile.dateOfBirth,
    gender: profile.gender,
    highestQualification: profile.highestQualification,
    degreeField: profile.degreeField,
    academicClassification: profile.academicClassification,
    graduationYear: profile.graduationYear,
    workExperienceYears: profile.workExperienceYears,
    preferredStudyLevels: profile.preferredStudyLevels,
    preferredCountries: countries,
    areasOfInterest: profile.areasOfInterest,
    englishTestStatus: profile.englishTestStatus,
    passportStatus: profile.passportStatus,
    employmentStatus: profile.employmentStatus,
    fundingPreferences: profile.fundingPreferences,
    specialEligibilityCategories: profile.specialEligibilityCategories,
    documents: profile.documents,
  );
}
