import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/opportunities/domain/opportunity.dart';
import 'package:scholarsphere/features/profiles/domain/applicant_profile.dart';
import 'package:scholarsphere/features/recommendations/domain/recommendation.dart';
import 'package:scholarsphere/features/recommendations/domain/recommendation_engine.dart';
import 'package:scholarsphere/features/search/domain/opportunity_filter.dart';
import 'package:scholarsphere/features/search/domain/opportunity_search.dart';

void main() {
  test('Canada belongs to North America and its popular filter', () {
    expect(Geography.regionFor('Canada'), GeographicRegion.northAmerica);
    expect(Geography.matches('Canada', GeographicRegion.northAmerica), isTrue);
    expect(Geography.matches('Canada', GeographicRegion.canada), isTrue);
  });

  test('structured search combines region, funding, and fee filters', () async {
    final opportunities = await DemoOpportunityRepository().getPublished();
    final results = const OpportunitySearch().apply(
      opportunities,
      const OpportunityFilter(
        region: GeographicRegion.europe,
        funding: FundingType.fullyFunded,
        noApplicationFee: true,
      ),
      now: DateTime(2026, 7, 28),
    );

    expect(results.length, 2);
    expect(results.every((item) => item.applicationFee == 0), isTrue);
  });

  test('recommendation categories select relevant opportunities', () async {
    final opportunities = await DemoOpportunityRepository().getPublished();
    final profile = ApplicantProfile(
      userId: 'user',
      fullName: 'Applicant',
      nationality: 'Ghana',
      countryOfResidence: 'Ghana',
      dateOfBirth: null,
      gender: '',
      highestQualification: '',
      degreeField: 'Public policy',
      academicClassification: '',
      graduationYear: null,
      workExperienceYears: 1,
      preferredStudyLevels: const ['Graduate'],
      preferredCountries: const ['Germany'],
      areasOfInterest: const ['Climate'],
      englishTestStatus: EnglishTestStatus.completed,
      passportStatus: PassportStatus.valid,
      employmentStatus: EmploymentStatus.student,
      fundingPreferences: const ['Fully funded'],
      specialEligibilityCategories: const [],
      documents: const [],
    );

    final recommendations = const RecommendationEngine().recommend(
      opportunities: opportunities,
      profile: profile,
      category: RecommendationCategory.online,
      now: DateTime(2026, 7, 28),
    );

    expect(recommendations.length, 1);
    expect(recommendations.first.opportunity.hostCountry, 'Remote');
  });
}
