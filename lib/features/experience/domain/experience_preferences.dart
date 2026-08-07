enum SupportedLanguage {
  english('en', false),
  french('fr', false),
  spanish('es', false),
  arabic('ar', true);

  const SupportedLanguage(this.code, this.isRightToLeft);
  final String code;
  final bool isRightToLeft;
}

class ExperiencePreferences {
  const ExperiencePreferences({
    this.language = SupportedLanguage.english,
    this.timezone = 'UTC',
    this.currencyCode = 'USD',
    this.countryCode = 'US',
    this.textScale = 1,
    this.highContrast = false,
    this.screenReaderOptimized = false,
    this.keyboardNavigation = true,
    this.lowBandwidthMode = false,
    this.compressImages = true,
    this.dataSaving = false,
    this.cacheSavedOpportunities = true,
  });

  final SupportedLanguage language;
  final String timezone;
  final String currencyCode;
  final String countryCode;
  final double textScale;
  final bool highContrast;
  final bool screenReaderOptimized;
  final bool keyboardNavigation;
  final bool lowBandwidthMode;
  final bool compressImages;
  final bool dataSaving;
  final bool cacheSavedOpportunities;

  ExperiencePreferences copyWith({
    SupportedLanguage? language,
    String? timezone,
    String? currencyCode,
    String? countryCode,
    double? textScale,
    bool? highContrast,
    bool? screenReaderOptimized,
    bool? keyboardNavigation,
    bool? lowBandwidthMode,
    bool? compressImages,
    bool? dataSaving,
    bool? cacheSavedOpportunities,
  }) => ExperiencePreferences(
    language: language ?? this.language,
    timezone: timezone ?? this.timezone,
    currencyCode: currencyCode ?? this.currencyCode,
    countryCode: countryCode ?? this.countryCode,
    textScale: textScale ?? this.textScale,
    highContrast: highContrast ?? this.highContrast,
    screenReaderOptimized: screenReaderOptimized ?? this.screenReaderOptimized,
    keyboardNavigation: keyboardNavigation ?? this.keyboardNavigation,
    lowBandwidthMode: lowBandwidthMode ?? this.lowBandwidthMode,
    compressImages: compressImages ?? this.compressImages,
    dataSaving: dataSaving ?? this.dataSaving,
    cacheSavedOpportunities:
        cacheSavedOpportunities ?? this.cacheSavedOpportunities,
  );
}

class TranslationEntry {
  const TranslationEntry({
    required this.key,
    required this.language,
    required this.value,
    required this.updatedAt,
    required this.updatedBy,
  });
  final String key;
  final SupportedLanguage language;
  final String value;
  final DateTime updatedAt;
  final String updatedBy;
}
