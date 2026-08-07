class RankedMetric {
  const RankedMetric({required this.label, required this.value});

  final String label;
  final num value;
}

class AdministrationDashboardSnapshot {
  const AdministrationDashboardSnapshot({
    required this.totalOpportunities,
    required this.activeOpportunities,
    required this.verifiedOpportunities,
    required this.pendingVerification,
    required this.expiredOpportunities,
    required this.suspiciousSubmissions,
    required this.registeredApplicants,
    required this.registeredProviders,
    required this.trackedApplications,
    required this.mostViewed,
    required this.popularCountries,
    required this.popularFields,
    required this.closingSoon,
    required this.notificationStatistics,
  });

  final int totalOpportunities;
  final int activeOpportunities;
  final int verifiedOpportunities;
  final int pendingVerification;
  final int expiredOpportunities;
  final int suspiciousSubmissions;
  final int registeredApplicants;
  final int registeredProviders;
  final int trackedApplications;
  final List<RankedMetric> mostViewed;
  final List<RankedMetric> popularCountries;
  final List<RankedMetric> popularFields;
  final List<RankedMetric> closingSoon;
  final List<RankedMetric> notificationStatistics;
}

class ReportingSnapshot {
  const ReportingSnapshot({
    required this.opportunitiesByCountry,
    required this.opportunitiesByContinent,
    required this.scholarshipsByStudyLevel,
    required this.opportunitiesByFunding,
    required this.applicationConversionRate,
    required this.userInterestByField,
    required this.successfulProviders,
    required this.verificationActivity,
    required this.expiredOpportunityReport,
    required this.notificationEngagement,
    required this.applicationOutcomes,
  });

  final List<RankedMetric> opportunitiesByCountry;
  final List<RankedMetric> opportunitiesByContinent;
  final List<RankedMetric> scholarshipsByStudyLevel;
  final List<RankedMetric> opportunitiesByFunding;
  final double applicationConversionRate;
  final List<RankedMetric> userInterestByField;
  final List<RankedMetric> successfulProviders;
  final List<RankedMetric> verificationActivity;
  final List<RankedMetric> expiredOpportunityReport;
  final double notificationEngagement;
  final List<RankedMetric> applicationOutcomes;
}

class AdministrationData {
  const AdministrationData({required this.dashboard, required this.reports});

  final AdministrationDashboardSnapshot dashboard;
  final ReportingSnapshot reports;
}
