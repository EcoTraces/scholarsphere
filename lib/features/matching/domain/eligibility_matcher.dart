import '../../opportunities/domain/opportunity.dart';
import '../../profiles/domain/applicant_profile.dart';
import 'eligibility_match.dart';

class EligibilityMatcher {
  const EligibilityMatcher();

  EligibilityMatch evaluate(ApplicantProfile profile, Opportunity opportunity) {
    final conditions = <MatchCondition>[
      _nationality(profile, opportunity),
      _studyLevel(profile, opportunity),
      _field(profile, opportunity),
      _age(profile, opportunity),
      _experience(profile, opportunity),
      _language(profile, opportunity),
      _applicationFee(opportunity),
      _funding(profile, opportunity),
    ];
    final earned = conditions.fold<double>(
      0,
      (total, item) =>
          total +
          switch (item.status) {
            MatchConditionStatus.matched => 1,
            MatchConditionStatus.uncertain => 0.5,
            MatchConditionStatus.missing => 0,
          },
    );
    return EligibilityMatch(
      score: ((earned / conditions.length) * 100).round(),
      conditions: conditions,
    );
  }

  MatchCondition _nationality(
    ApplicantProfile profile,
    Opportunity opportunity,
  ) {
    if (_contains(opportunity.eligibleNationalities, 'all nationalities')) {
      return _matched('Nationality', 'Open to all nationalities.');
    }
    if (profile.nationality.isEmpty) {
      return _uncertain(
        'Nationality',
        'Add your nationality to evaluate this requirement.',
      );
    }
    return _contains(opportunity.eligibleNationalities, profile.nationality)
        ? _matched('Nationality', 'Your nationality is eligible.')
        : _missing(
            'Nationality',
            'Your nationality is not listed as eligible.',
          );
  }

  MatchCondition _studyLevel(
    ApplicantProfile profile,
    Opportunity opportunity,
  ) {
    if (profile.preferredStudyLevels.isEmpty) {
      return _uncertain('Academic level', 'Add your preferred study level.');
    }
    return _overlaps(profile.preferredStudyLevels, opportunity.studyLevels)
        ? _matched('Academic level', 'Your preferred level is offered.')
        : _missing('Academic level', 'Your preferred level does not match.');
  }

  MatchCondition _field(ApplicantProfile profile, Opportunity opportunity) {
    if (_contains(opportunity.fieldsOfStudy, 'all fields')) {
      return _matched('Field of study', 'All fields are eligible.');
    }
    final fields = [
      profile.degreeField,
      ...profile.areasOfInterest,
    ].where((item) => item.isNotEmpty).toList();
    if (fields.isEmpty) {
      return _uncertain(
        'Field of study',
        'Add your degree field or interests.',
      );
    }
    return _overlaps(fields, opportunity.fieldsOfStudy)
        ? _matched('Field of study', 'Your field is relevant.')
        : _missing('Field of study', 'Your field is not listed.');
  }

  MatchCondition _age(ApplicantProfile profile, Opportunity opportunity) {
    if (opportunity.minimumAge == null && opportunity.maximumAge == null) {
      return _matched('Age', 'No age restriction is listed.');
    }
    final birthDate = profile.dateOfBirth;
    if (birthDate == null) {
      return _uncertain(
        'Age',
        'Add your date of birth to check the age limit.',
      );
    }
    final now = DateTime.now();
    var age = now.year - birthDate.year;
    if (now.month < birthDate.month ||
        (now.month == birthDate.month && now.day < birthDate.day)) {
      age--;
    }
    final aboveMinimum =
        opportunity.minimumAge == null || age >= opportunity.minimumAge!;
    final belowMaximum =
        opportunity.maximumAge == null || age <= opportunity.maximumAge!;
    return aboveMinimum && belowMaximum
        ? _matched('Age', 'You meet the listed age requirement.')
        : _missing('Age', 'You do not meet the listed age requirement.');
  }

  MatchCondition _experience(
    ApplicantProfile profile,
    Opportunity opportunity,
  ) {
    final required = opportunity.workExperienceYearsRequired;
    if (required == null || required == 0) {
      return _matched('Work experience', 'No experience minimum is listed.');
    }
    return profile.workExperienceYears >= required
        ? _matched('Work experience', 'You meet the experience requirement.')
        : _missing(
            'Work experience',
            '${_years(required)} of work experience required.',
          );
  }

  MatchCondition _language(ApplicantProfile profile, Opportunity opportunity) {
    if (opportunity.languageRequirements.isEmpty) {
      return _matched('Language', 'No language requirement is listed.');
    }
    return switch (profile.englishTestStatus) {
      EnglishTestStatus.completed || EnglishTestStatus.notRequired => _matched(
        'Language',
        'Your language-test status is ready.',
      ),
      EnglishTestStatus.planned => _uncertain(
        'Language',
        'Your language test is planned but not completed.',
      ),
      EnglishTestStatus.notTaken => _missing(
        'Language',
        'A language requirement is listed but no test is recorded.',
      ),
    };
  }

  MatchCondition _applicationFee(Opportunity opportunity) {
    final fee = opportunity.applicationFee;
    if (fee == null) {
      return _uncertain('Application fee', 'The application fee is unknown.');
    }
    return fee == 0
        ? _matched('Application fee', 'No application fee.')
        : _matched('Application fee', 'An application fee is required.');
  }

  MatchCondition _funding(ApplicantProfile profile, Opportunity opportunity) {
    if (profile.fundingPreferences.isEmpty) {
      return _uncertain('Funding', 'Add your funding preference.');
    }
    return _contains(profile.fundingPreferences, opportunity.fundingLabel)
        ? _matched('Funding', 'The funding matches your preference.')
        : _missing('Funding', 'The funding differs from your preference.');
  }

  bool _contains(List<String> values, String target) =>
      values.any((value) => value.toLowerCase() == target.toLowerCase());

  bool _overlaps(List<String> left, List<String> right) => left.any(
    (value) => right.any(
      (other) =>
          other.toLowerCase().contains(value.toLowerCase()) ||
          value.toLowerCase().contains(other.toLowerCase()),
    ),
  );

  MatchCondition _matched(String label, String explanation) => MatchCondition(
    label: label,
    status: MatchConditionStatus.matched,
    explanation: explanation,
  );

  MatchCondition _missing(String label, String explanation) => MatchCondition(
    label: label,
    status: MatchConditionStatus.missing,
    explanation: explanation,
  );

  MatchCondition _uncertain(String label, String explanation) => MatchCondition(
    label: label,
    status: MatchConditionStatus.uncertain,
    explanation: explanation,
  );

  String _years(double value) =>
      '${value == value.roundToDouble() ? value.toInt() : value} '
      '${value == 1 ? 'year' : 'years'}';
}
