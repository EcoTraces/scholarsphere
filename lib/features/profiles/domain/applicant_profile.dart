import '../../authentication/domain/user_account.dart';

enum EnglishTestStatus { notTaken, planned, completed, notRequired }

enum PassportStatus { unavailable, applied, valid, expired }

enum EmploymentStatus { student, employed, selfEmployed, unemployed, other }

class ProfileDocument {
  const ProfileDocument({
    required this.id,
    required this.name,
    required this.type,
    required this.uploadedAt,
  });

  final String id;
  final String name;
  final String type;
  final DateTime uploadedAt;
}

class ApplicantProfile {
  const ApplicantProfile({
    required this.userId,
    required this.fullName,
    required this.nationality,
    required this.countryOfResidence,
    required this.dateOfBirth,
    required this.gender,
    required this.highestQualification,
    required this.degreeField,
    required this.academicClassification,
    required this.graduationYear,
    required this.workExperienceYears,
    required this.preferredStudyLevels,
    required this.preferredCountries,
    required this.areasOfInterest,
    required this.englishTestStatus,
    required this.passportStatus,
    required this.employmentStatus,
    required this.fundingPreferences,
    required this.specialEligibilityCategories,
    required this.documents,
  });

  factory ApplicantProfile.empty(UserAccount account) => ApplicantProfile(
    userId: account.id,
    fullName: account.fullName,
    nationality: '',
    countryOfResidence: '',
    dateOfBirth: null,
    gender: '',
    highestQualification: '',
    degreeField: '',
    academicClassification: '',
    graduationYear: null,
    workExperienceYears: 0,
    preferredStudyLevels: const [],
    preferredCountries: const [],
    areasOfInterest: const [],
    englishTestStatus: EnglishTestStatus.notTaken,
    passportStatus: PassportStatus.unavailable,
    employmentStatus: EmploymentStatus.student,
    fundingPreferences: const [],
    specialEligibilityCategories: const [],
    documents: const [],
  );

  final String userId;
  final String fullName;
  final String nationality;
  final String countryOfResidence;
  final DateTime? dateOfBirth;
  final String gender;
  final String highestQualification;
  final String degreeField;
  final String academicClassification;
  final int? graduationYear;
  final double workExperienceYears;
  final List<String> preferredStudyLevels;
  final List<String> preferredCountries;
  final List<String> areasOfInterest;
  final EnglishTestStatus englishTestStatus;
  final PassportStatus passportStatus;
  final EmploymentStatus employmentStatus;
  final List<String> fundingPreferences;
  final List<String> specialEligibilityCategories;
  final List<ProfileDocument> documents;

  ApplicantProfile copyWith({List<String>? preferredCountries}) =>
      ApplicantProfile(
        userId: userId,
        fullName: fullName,
        nationality: nationality,
        countryOfResidence: countryOfResidence,
        dateOfBirth: dateOfBirth,
        gender: gender,
        highestQualification: highestQualification,
        degreeField: degreeField,
        academicClassification: academicClassification,
        graduationYear: graduationYear,
        workExperienceYears: workExperienceYears,
        preferredStudyLevels: preferredStudyLevels,
        preferredCountries: preferredCountries ?? this.preferredCountries,
        areasOfInterest: areasOfInterest,
        englishTestStatus: englishTestStatus,
        passportStatus: passportStatus,
        employmentStatus: employmentStatus,
        fundingPreferences: fundingPreferences,
        specialEligibilityCategories: specialEligibilityCategories,
        documents: documents,
      );
}
