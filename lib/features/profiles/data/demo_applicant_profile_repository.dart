import '../domain/applicant_profile.dart';
import '../domain/applicant_profile_repository.dart';

class DemoApplicantProfileRepository implements ApplicantProfileRepository {
  final Map<String, ApplicantProfile> _profiles = {};

  @override
  Future<ApplicantProfile?> getForUser(String userId) async =>
      _profiles[userId];

  @override
  Future<void> save(ApplicantProfile profile) async {
    _profiles[profile.userId] = profile;
  }

  @override
  Future<List<ApplicantProfile>> getAllForAdministration() async =>
      _profiles.values.toList();
}
