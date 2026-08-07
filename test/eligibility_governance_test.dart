import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/eligibility_rules/data/demo_eligibility_rule_repository.dart';
import 'package:scholarsphere/features/eligibility_rules/domain/eligibility_rule.dart';
import 'package:scholarsphere/features/eligibility_rules/domain/eligibility_rule_evaluator.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/profiles/domain/applicant_profile.dart';
import 'package:scholarsphere/features/recommendations/data/demo_recommendation_governance_repository.dart';
import 'package:scholarsphere/features/recommendations/domain/governed_recommendation_service.dart';
import 'package:scholarsphere/features/recommendations/domain/recommendation.dart';
import 'package:scholarsphere/features/recommendations/domain/recommendation_governance.dart';

void main() {
  test(
    'eligibility rules are versioned and return auditable explanations',
    () async {
      final repository = DemoEligibilityRuleRepository(
        clock: () => DateTime.utc(2026, 7, 29),
      );
      final first = await repository.createVersion(
        opportunityId: 'opportunity-1',
        createdBy: 'officer',
        rules: const [
          EligibilityRule(
            id: 'nationality',
            label: 'Eligible nationality',
            type: EligibilityRuleType.mandatory,
            attribute: EligibilityAttribute.nationality,
            operator: EligibilityOperator.oneOf,
            values: ['Ghana', 'Kenya'],
            weight: 60,
            officialSource: true,
          ),
          EligibilityRule(
            id: 'experience',
            label: 'Two years of experience',
            type: EligibilityRuleType.preferred,
            attribute: EligibilityAttribute.workExperienceYears,
            operator: EligibilityOperator.minimum,
            values: ['2'],
            weight: 40,
            officialSource: true,
          ),
        ],
      );
      final second = await repository.createVersion(
        opportunityId: 'opportunity-1',
        createdBy: 'officer',
        rules: first.rules,
      );

      expect(first.isActive, isTrue);
      expect(
        (await repository.getVersions('opportunity-1')).first.isActive,
        isFalse,
      );
      expect(second.version, 2);

      final result = const EligibilityRuleEvaluator().evaluate(
        profile: _profile(),
        ruleSet: second,
      );
      expect(result.percentage, 100);
      expect(result.mandatoryMet, hasLength(1));
      expect(result.ruleVersion, 2);
      expect(result.disclaimer, contains('Confirm all requirements'));
    },
  );

  test(
    'manual override is identified without hiding missing information',
    () async {
      final now = DateTime.utc(2026, 7, 29);
      final set = EligibilityRuleSet(
        id: 'rules-1',
        opportunityId: 'opportunity-1',
        version: 1,
        createdAt: now,
        createdBy: 'officer',
        isActive: true,
        rules: const [
          EligibilityRule(
            id: 'disability',
            label: 'Disability category',
            type: EligibilityRuleType.optional,
            attribute: EligibilityAttribute.disabilityCategory,
            operator: EligibilityOperator.present,
            values: [],
            weight: 20,
            officialSource: false,
          ),
        ],
      );
      final result = const EligibilityRuleEvaluator().evaluate(
        profile: _profile(),
        ruleSet: set,
        overrides: [
          EligibilityOverride(
            ruleId: 'disability',
            status: RuleEvaluationStatus.uncertain,
            reason: 'Evidence review pending',
            officerId: 'officer',
            createdAt: now,
          ),
        ],
      );

      expect(result.uncertainRequirements.single.manuallyOverridden, isTrue);
      expect(result.officialSourceWarning, contains('not confirmed'));
    },
  );

  test(
    'governance respects opt-out, labels sponsorship, and suppresses dismissal',
    () async {
      final repository = DemoRecommendationGovernanceRepository();
      await repository.saveControls(
        'user',
        const PersonalizationControls(behaviouralRecommendationsEnabled: false),
      );
      final service = GovernedRecommendationService(
        repository: repository,
        clock: () => DateTime(2026, 7, 28),
      );
      final opportunities = await DemoOpportunityRepository().getPublished();
      final first = await service.recommend(
        userId: 'user',
        opportunities: opportunities,
        profile: _profile(),
        category: RecommendationCategory.bestMatches,
        signals: const RecommendationSignals(previousSearches: ['climate']),
        sponsoredOpportunityIds: {opportunities.first.id},
      );

      expect(
        first.first.explanation,
        contains('Behavioural personalization is disabled.'),
      );
      expect(
        first
            .where((item) => item.isSponsored)
            .single
            .labels
            .contains(RecommendationLabel.sponsoredOpportunity),
        isTrue,
      );

      await repository.recordFeedback(
        RecommendationFeedback(
          userId: 'user',
          opportunityId: first.first.recommendation.opportunity.id,
          type: RecommendationFeedbackType.dismissed,
          createdAt: DateTime(2026, 7, 29),
        ),
      );
      final second = await service.recommend(
        userId: 'user',
        opportunities: opportunities,
        profile: _profile(),
        category: RecommendationCategory.bestMatches,
      );
      expect(
        second.any(
          (item) =>
              item.recommendation.opportunity.id ==
              first.first.recommendation.opportunity.id,
        ),
        isFalse,
      );
      expect((await repository.qualityReport()).dismissalRate, greaterThan(0));
      await repository.resetHistory('user');
      expect(await repository.getHistory('user'), isEmpty);
    },
  );
}

ApplicantProfile _profile() => ApplicantProfile(
  userId: 'user',
  fullName: 'Applicant',
  nationality: 'Ghana',
  countryOfResidence: 'Ghana',
  dateOfBirth: DateTime(2000, 1, 1),
  gender: '',
  highestQualification: 'Bachelor',
  degreeField: 'Computer science',
  academicClassification: 'First class',
  graduationYear: 2024,
  workExperienceYears: 2,
  preferredStudyLevels: const ['Master'],
  preferredCountries: const ['United Kingdom'],
  areasOfInterest: const ['Technology'],
  englishTestStatus: EnglishTestStatus.completed,
  passportStatus: PassportStatus.valid,
  employmentStatus: EmploymentStatus.employed,
  fundingPreferences: const ['Fully funded'],
  specialEligibilityCategories: const [],
  documents: const [],
);
