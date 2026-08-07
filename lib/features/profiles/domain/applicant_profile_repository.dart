import 'applicant_profile.dart';

abstract interface class ApplicantProfileRepository {
  Future<ApplicantProfile?> getForUser(String userId);

  Future<void> save(ApplicantProfile profile);

  Future<List<ApplicantProfile>> getAllForAdministration();
}
