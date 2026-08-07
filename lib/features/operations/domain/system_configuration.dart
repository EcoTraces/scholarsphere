enum FeatureFlag {
  whatsappNotifications,
  aiRecommendations,
  automatedCollection,
  providerSelfPublication,
  premiumSubscription,
  documentAnalysis,
  newMobileFeatures,
  experimentalSearch,
}

class PlatformConfiguration {
  const PlatformConfiguration({
    required this.version,
    required this.platformName,
    required this.logoLocation,
    required this.brandPrimaryColor,
    required this.emailSenderName,
    required this.emailSenderAddress,
    required this.verificationExpirationDays,
    required this.supportedCountries,
    required this.supportedLanguages,
    required this.opportunityCategories,
    required this.documentTypes,
    required this.maximumFileSizeBytes,
    required this.applicantRegistrationEnabled,
    required this.providerRegistrationEnabled,
    required this.maintenanceMode,
    required this.featureFlags,
    required this.environment,
    required this.securityPolicy,
    required this.recommendationSettings,
    required this.fraudRuleSettings,
    required this.integrationSettings,
    required this.notificationSettings,
    required this.updatedAt,
    required this.updatedBy,
    required this.changeReason,
  });

  factory PlatformConfiguration.defaults() => PlatformConfiguration(
    version: 1,
    platformName: 'ScholarSphere',
    logoLocation: 'assets/branding/logo.png',
    brandPrimaryColor: '#007C72',
    emailSenderName: 'ScholarSphere',
    emailSenderAddress: 'no-reply@scholarsphere.example',
    verificationExpirationDays: 90,
    supportedCountries: const ['Global'],
    supportedLanguages: const ['en'],
    opportunityCategories: const ['scholarship', 'fellowship', 'internship'],
    documentTypes: const ['passport', 'transcript', 'curriculum_vitae'],
    maximumFileSizeBytes: 10 * 1024 * 1024,
    applicantRegistrationEnabled: true,
    providerRegistrationEnabled: true,
    maintenanceMode: false,
    featureFlags: const {
      FeatureFlag.whatsappNotifications: false,
      FeatureFlag.aiRecommendations: false,
      FeatureFlag.automatedCollection: false,
      FeatureFlag.providerSelfPublication: false,
      FeatureFlag.premiumSubscription: false,
      FeatureFlag.documentAnalysis: false,
      FeatureFlag.newMobileFeatures: false,
      FeatureFlag.experimentalSearch: false,
    },
    environment: const {'name': 'development', 'apiVersion': 'v1'},
    securityPolicy: const {
      'minimumPasswordLength': 12,
      'mfaForAdministrators': true,
    },
    recommendationSettings: const {'diversityEnabled': true, 'limit': 20},
    fraudRuleSettings: const {'automaticHideScore': 90},
    integrationSettings: const {'sandboxEnabled': true},
    notificationSettings: const {'dailyLimit': 10},
    updatedAt: null,
    updatedBy: 'system',
    changeReason: 'Initial configuration',
  );

  final int version;
  final String platformName;
  final String logoLocation;
  final String brandPrimaryColor;
  final String emailSenderName;
  final String emailSenderAddress;
  final int verificationExpirationDays;
  final List<String> supportedCountries;
  final List<String> supportedLanguages;
  final List<String> opportunityCategories;
  final List<String> documentTypes;
  final int maximumFileSizeBytes;
  final bool applicantRegistrationEnabled;
  final bool providerRegistrationEnabled;
  final bool maintenanceMode;
  final Map<FeatureFlag, bool> featureFlags;
  final Map<String, Object> environment;
  final Map<String, Object> securityPolicy;
  final Map<String, Object> recommendationSettings;
  final Map<String, Object> fraudRuleSettings;
  final Map<String, Object> integrationSettings;
  final Map<String, Object> notificationSettings;
  final DateTime? updatedAt;
  final String updatedBy;
  final String changeReason;

  bool enabled(FeatureFlag flag) => featureFlags[flag] ?? false;

  PlatformConfiguration copyWith({
    int? version,
    String? platformName,
    String? logoLocation,
    String? brandPrimaryColor,
    String? emailSenderName,
    String? emailSenderAddress,
    int? verificationExpirationDays,
    List<String>? supportedCountries,
    List<String>? supportedLanguages,
    List<String>? opportunityCategories,
    List<String>? documentTypes,
    int? maximumFileSizeBytes,
    bool? applicantRegistrationEnabled,
    bool? providerRegistrationEnabled,
    bool? maintenanceMode,
    Map<FeatureFlag, bool>? featureFlags,
    Map<String, Object>? environment,
    Map<String, Object>? securityPolicy,
    Map<String, Object>? recommendationSettings,
    Map<String, Object>? fraudRuleSettings,
    Map<String, Object>? integrationSettings,
    Map<String, Object>? notificationSettings,
    DateTime? updatedAt,
    String? updatedBy,
    String? changeReason,
  }) => PlatformConfiguration(
    version: version ?? this.version,
    platformName: platformName ?? this.platformName,
    logoLocation: logoLocation ?? this.logoLocation,
    brandPrimaryColor: brandPrimaryColor ?? this.brandPrimaryColor,
    emailSenderName: emailSenderName ?? this.emailSenderName,
    emailSenderAddress: emailSenderAddress ?? this.emailSenderAddress,
    verificationExpirationDays:
        verificationExpirationDays ?? this.verificationExpirationDays,
    supportedCountries: supportedCountries ?? this.supportedCountries,
    supportedLanguages: supportedLanguages ?? this.supportedLanguages,
    opportunityCategories: opportunityCategories ?? this.opportunityCategories,
    documentTypes: documentTypes ?? this.documentTypes,
    maximumFileSizeBytes: maximumFileSizeBytes ?? this.maximumFileSizeBytes,
    applicantRegistrationEnabled:
        applicantRegistrationEnabled ?? this.applicantRegistrationEnabled,
    providerRegistrationEnabled:
        providerRegistrationEnabled ?? this.providerRegistrationEnabled,
    maintenanceMode: maintenanceMode ?? this.maintenanceMode,
    featureFlags: featureFlags ?? this.featureFlags,
    environment: environment ?? this.environment,
    securityPolicy: securityPolicy ?? this.securityPolicy,
    recommendationSettings:
        recommendationSettings ?? this.recommendationSettings,
    fraudRuleSettings: fraudRuleSettings ?? this.fraudRuleSettings,
    integrationSettings: integrationSettings ?? this.integrationSettings,
    notificationSettings: notificationSettings ?? this.notificationSettings,
    updatedAt: updatedAt ?? this.updatedAt,
    updatedBy: updatedBy ?? this.updatedBy,
    changeReason: changeReason ?? this.changeReason,
  );
}
