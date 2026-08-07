import 'dart:convert';

import '../../applications/domain/application_repository.dart';
import '../../authentication/domain/user_account.dart';
import '../../documents/domain/document_repository.dart';
import '../../profiles/domain/applicant_profile_repository.dart';
import 'privacy_repository.dart';

class PrivacyDataExportService {
  const PrivacyDataExportService({
    required this.profileRepository,
    required this.applicationRepository,
    required this.documentRepository,
    required this.privacyRepository,
  });

  final ApplicantProfileRepository profileRepository;
  final ApplicationRepository applicationRepository;
  final DocumentRepository documentRepository;
  final PrivacyRepository privacyRepository;

  Future<String> export(UserAccount user) async {
    final profile = await profileRepository.getForUser(user.id);
    final applications = await applicationRepository.getForUser(user.id);
    final documents = await documentRepository.getForUser(user.id);
    final consents = await privacyRepository.getConsents(user.id);
    final access = await privacyRepository.getAccessHistory(user.id);
    return const JsonEncoder.withIndent('  ').convert({
      'account': {
        'id': user.id,
        'fullName': user.fullName,
        'email': user.email,
        'role': user.role.name,
        'status': user.status.name,
      },
      'profile': profile == null
          ? null
          : {
              'nationality': profile.nationality,
              'countryOfResidence': profile.countryOfResidence,
              'dateOfBirth': profile.dateOfBirth?.toIso8601String(),
              'highestQualification': profile.highestQualification,
              'degreeField': profile.degreeField,
              'preferredCountries': profile.preferredCountries,
              'areasOfInterest': profile.areasOfInterest,
            },
      'applications': applications
          .map(
            (item) => {
              'opportunityId': item.opportunityId,
              'title': item.opportunityTitle,
              'stage': item.stage.name,
              'updatedAt': item.updatedAt.toIso8601String(),
            },
          )
          .toList(),
      'documents': documents
          .map(
            (item) => {
              'id': item.id,
              'type': item.type.name,
              'fileName': item.fileName,
              'encryptedAtRest': item.encryptedAtRest,
              'sharedWithProviderIds': item.sharedWithProviderIds.toList(),
            },
          )
          .toList(),
      'consents': consents
          .map(
            (item) => {
              'type': item.type.name,
              'policyVersion': item.policyVersion,
              'grantedAt': item.grantedAt.toIso8601String(),
              'withdrawnAt': item.withdrawnAt?.toIso8601String(),
            },
          )
          .toList(),
      'organizationAccess': access
          .map(
            (item) => {
              'organization': item.organizationName,
              'dataCategories': item.dataCategories.toList(),
              'accessedAt': item.accessedAt.toIso8601String(),
            },
          )
          .toList(),
    });
  }
}
