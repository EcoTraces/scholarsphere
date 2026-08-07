import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/matching/domain/eligibility_matcher.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/profiles/domain/applicant_profile.dart';

void main() {
  test('matching engine explains a strong applicant match', () async {
    final opportunity =
        (await DemoOpportunityRepository().getPublished()).first;
    final profile = ApplicantProfile(
      userId: 'applicant',
      fullName: 'Test Applicant',
      nationality: 'Ghana',
      countryOfResidence: 'Ghana',
      dateOfBirth: DateTime(2000, 1, 1),
      gender: '',
      highestQualification: 'Bachelor',
      degreeField: 'Computer science',
      academicClassification: 'First class',
      graduationYear: 2024,
      workExperienceYears: 2,
      preferredStudyLevels: const ['Master\'s'],
      preferredCountries: const ['United Kingdom'],
      areasOfInterest: const ['Technology'],
      englishTestStatus: EnglishTestStatus.completed,
      passportStatus: PassportStatus.valid,
      employmentStatus: EmploymentStatus.employed,
      fundingPreferences: const ['Fully funded'],
      specialEligibilityCategories: const [],
      documents: const [],
    );

    final result = const EligibilityMatcher().evaluate(profile, opportunity);

    expect(result.score, 100);
    expect(result.strength, 'Strong match');
    expect(result.missing, isEmpty);
    expect(result.matched, isNotEmpty);
  });
}
