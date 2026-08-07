import 'privacy_models.dart';

abstract final class PrivacyRules {
  static bool isMinor(DateTime? dateOfBirth, DateTime now) {
    if (dateOfBirth == null) return false;
    var age = now.year - dateOfBirth.year;
    if (now.month < dateOfBirth.month ||
        (now.month == dateOfBirth.month && now.day < dateOfBirth.day)) {
      age--;
    }
    return age < 18;
  }

  static bool minorCanGrant(ConsentType type) => !{
    ConsentType.marketing,
    ConsentType.thirdPartySharing,
    ConsentType.personalizedRecommendations,
  }.contains(type);
}
