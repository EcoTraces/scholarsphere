import 'package:flutter/material.dart';

import '../features/administration/domain/administration_analytics_service.dart';
import '../features/administration/presentation/administration_dashboard_screen.dart';
import '../features/analytics/data/api_analytics_repository.dart';
import '../features/analytics/domain/analytics_repository.dart';
import '../features/audit/data/api_audit_repository.dart';
import '../features/audit/domain/audit_repository.dart';
import '../features/background_jobs/data/demo_job_queue_repository.dart';
import '../features/background_jobs/domain/background_job.dart';
import '../features/calendar/data/api_calendar_repository.dart';
import '../features/calendar/domain/calendar_repository.dart';
import '../features/calendar/presentation/calendar_screen.dart';
import '../features/authentication/data/firebase_auth_repository.dart';
import '../features/authentication/domain/auth_repository.dart';
import '../features/authentication/domain/user_account.dart';
import '../features/authentication/presentation/auth_screen.dart';
import '../features/authentication/presentation/role_workspace_screen.dart';
import '../features/applications/data/api_application_repository.dart';
import '../features/applications/domain/application_repository.dart';
import '../features/applications/presentation/application_tracker_screen.dart';
import '../features/collection/data/api_opportunity_collection_repository.dart';
import '../features/collection/domain/opportunity_collection_repository.dart';
import '../features/dashboard/presentation/applicant_dashboard_screen.dart';
import '../features/documents/data/api_document_repository.dart';
import '../features/documents/domain/document_repository.dart';
import '../features/experience/data/api_experience_repository.dart';
import '../features/experience/domain/experience_repository.dart';
import '../features/experience/domain/experience_preferences.dart';
import '../features/fraud_investigation/data/api_fraud_investigation_repository.dart';
import '../features/fraud_investigation/domain/fraud_investigation_repository.dart';
import '../features/governance/data/api_data_lifecycle_repository.dart';
import '../features/governance/data/api_legal_compliance_repository.dart';
import '../features/governance/domain/data_lifecycle_repository.dart';
import '../features/governance/domain/legal_compliance_repository.dart';
import '../features/governance/domain/data_lifecycle.dart';
import '../features/guidance/data/api_application_guidance_repository.dart';
import '../features/guidance/domain/application_guidance_repository.dart';
import '../features/moderation/data/api_moderation_repository.dart';
import '../features/moderation/domain/moderation_repository.dart';
import '../features/moderation/presentation/moderator_dashboard_screen.dart';
import '../features/opportunities/data/api_opportunity_repository.dart';
import '../features/opportunities/data/api_provider_opportunity_repository.dart';
import '../features/opportunities/data/demo_opportunity_repository.dart';
import '../features/opportunities/domain/opportunity_repository.dart';
import '../features/operations/data/api_backup_repository.dart';
import '../features/operations/data/api_observability_repository.dart';
import '../features/operations/data/api_release_repository.dart';
import '../features/operations/data/api_system_configuration_repository.dart';
import '../features/operations/domain/backup_repository.dart';
import '../features/operations/domain/observability_repository.dart';
import '../features/operations/domain/release_repository.dart';
import '../features/operations/domain/system_configuration_repository.dart';
import '../features/opportunities/presentation/discover_screen.dart';
import '../features/providers/data/api_provider_repository.dart';
import '../features/providers/presentation/provider_account_screen.dart';
import '../features/provider_analytics/data/api_provider_analytics_repository.dart';
import '../features/provider_analytics/domain/provider_analytics.dart';
import '../features/sources/data/api_source_registry_repository.dart';
import '../features/sources/domain/source_registry_repository.dart';
import '../features/notifications/data/api_notification_repository.dart';
import '../features/notifications/domain/notification_repository.dart';
import '../features/notifications/presentation/notification_center_screen.dart';
import '../features/profiles/data/api_applicant_profile_repository.dart';
import '../features/profiles/domain/applicant_profile_repository.dart';
import '../features/profiles/presentation/applicant_profile_screen.dart';
import '../features/premium/data/api_premium_repository.dart';
import '../features/premium/domain/premium_repository.dart';
import '../features/premium/presentation/premium_landing_screen.dart';
import '../features/testimonials/data/api_testimonial_repository.dart';
import '../features/testimonials/domain/testimonial_repository.dart';
import '../features/testimonials/presentation/share_success_story_screen.dart';
import '../features/testimonials/presentation/success_stories_screen.dart';
import '../features/privacy/data/api_privacy_repository.dart';
import '../features/privacy/domain/privacy_repository.dart';
import '../features/privacy/domain/privacy_models.dart';
import '../features/recommendations/data/api_recommendation_governance_repository.dart';
import '../features/recommendations/domain/recommendation_governance_repository.dart';
import '../features/security/data/api_security_repository.dart';
import '../features/security/domain/security_repository.dart';
import '../features/security/presentation/security_privacy_center_screen.dart';
import '../features/security/presentation/security_administrator_dashboard_screen.dart';
import '../features/search_index/data/api_search_index_repository.dart';
import '../features/search_index/domain/search_index_repository.dart';
import '../features/support/data/api_support_repository.dart';
import '../features/support/domain/support_repository.dart';
import '../features/support/presentation/support_agent_screen.dart';
import '../features/taxonomy/data/api_taxonomy_repository.dart';
import '../features/taxonomy/domain/taxonomy_repository.dart';
import '../features/security/domain/access_control.dart';
import '../features/verification/data/api_verification_repository.dart';
import '../features/verification/presentation/verification_officer_dashboard_screen.dart';
import 'theme.dart';

class ScholarSphereApp extends StatefulWidget {
  const ScholarSphereApp({
    super.key,
    this.authRepository,
    this.apiOpportunityRepository,
    this.applicationRepository,
    this.notificationRepository,
    this.applicantProfileRepository,
    this.documentRepository,
    this.moderationRepository,
    this.privacyRepository,
    this.supportRepository,
    this.sourceRegistryRepository,
    this.taxonomyRepository,
    this.calendarRepository,
    this.guidanceRepository,
    this.experienceRepository,
    this.searchIndexRepository,
    this.legalRepository,
    this.analyticsRepository,
    this.recommendationGovernanceRepository,
    this.providerAnalyticsRepository,
    this.securityRepository,
    this.auditRepository,
    this.systemConfigurationRepository,
    this.backupRepository,
    this.releaseRepository,
    this.dataLifecycleRepository,
    this.observabilityRepository,
    this.fraudInvestigationRepository,
    this.collectionRepository,
    this.verificationRepository,
    this.premiumRepository,
    this.testimonialRepository,
  });

  /// Overrides the real Firebase-backed auth repository. Production never
  /// sets this (it defaults to [FirebaseAuthRepository]); tests pass a
  /// [DemoAuthRepository] so widget tests never require a live Firebase app.
  final AuthRepository? authRepository;

  /// Overrides the real backend-backed opportunity repository used on the
  /// applicant Discover/Dashboard screens. Production never sets this (it
  /// defaults to [ApiOpportunityRepository]); tests pass a
  /// [DemoOpportunityRepository] so they never require the FastAPI backend
  /// to be running.
  final OpportunityRepository? apiOpportunityRepository;

  /// Overrides the real backend-backed application repository used on the
  /// applicant Discover/Dashboard screens. Production never sets this (it
  /// defaults to [ApiApplicationRepository]); tests pass a
  /// [DemoApplicationRepository] so they never require the FastAPI backend
  /// to be running.
  final ApplicationRepository? applicationRepository;

  /// Overrides the real backend-backed notification repository used on the
  /// applicant Discover/Dashboard screens. Production never sets this (it
  /// defaults to [ApiNotificationRepository]); tests pass a
  /// [DemoNotificationRepository] so they never require the FastAPI backend
  /// to be running.
  final NotificationRepository? notificationRepository;

  /// Overrides the real backend-backed applicant profile repository.
  /// Production never sets this (it defaults to
  /// [ApiApplicantProfileRepository]); tests pass a
  /// [DemoApplicantProfileRepository] so they never require the FastAPI
  /// backend to be running.
  final ApplicantProfileRepository? applicantProfileRepository;

  /// Overrides the real backend-backed document repository. Production
  /// never sets this (it defaults to [ApiDocumentRepository]); tests pass
  /// a [DemoDocumentRepository] so they never require the FastAPI backend
  /// to be running.
  final DocumentRepository? documentRepository;

  /// Overrides the real backend-backed moderation repository. Production
  /// never sets this (it defaults to [ApiModerationRepository]); tests
  /// pass a [DemoModerationRepository] so they never require the FastAPI
  /// backend to be running.
  final ModerationRepository? moderationRepository;

  /// Overrides the real backend-backed privacy repository. Production
  /// never sets this (it defaults to [ApiPrivacyRepository]); tests pass a
  /// [DemoPrivacyRepository] so they never require the FastAPI backend to
  /// be running.
  final PrivacyRepository? privacyRepository;

  /// Overrides the real backend-backed support ticketing repository.
  /// Production never sets this (it defaults to [ApiSupportRepository]);
  /// tests pass a [DemoSupportRepository] so they never require the
  /// FastAPI backend to be running.
  final SupportRepository? supportRepository;

  /// Overrides the real backend-backed source registry repository.
  /// Production never sets this (it defaults to
  /// [ApiSourceRegistryRepository]); tests pass a
  /// [DemoSourceRegistryRepository] so they never require the FastAPI
  /// backend to be running.
  final SourceRegistryRepository? sourceRegistryRepository;

  /// Overrides the real backend-backed taxonomy repository. Production
  /// never sets this (it defaults to [ApiTaxonomyRepository]); tests pass
  /// a [DemoTaxonomyRepository] so they never require the FastAPI backend
  /// to be running.
  final TaxonomyRepository? taxonomyRepository;

  /// Overrides the real backend-backed deadline calendar repository.
  /// Production never sets this (it defaults to
  /// [ApiCalendarRepository]); tests pass a [DemoCalendarRepository] so
  /// they never require the FastAPI backend to be running.
  final CalendarRepository? calendarRepository;

  /// Overrides the real backend-backed application guidance repository.
  /// Production never sets this (it defaults to
  /// [ApiApplicationGuidanceRepository]); tests pass a
  /// [DemoApplicationGuidanceRepository] so they never require the
  /// FastAPI backend to be running.
  final ApplicationGuidanceRepository? guidanceRepository;

  /// Overrides the real backend-backed accessibility/localization
  /// preferences repository. Production never sets this (it defaults to
  /// [ApiExperienceRepository]); tests pass a [DemoExperienceRepository]
  /// so they never require the FastAPI backend to be running.
  final ExperienceRepository? experienceRepository;

  /// Overrides the real backend-backed search index repository.
  /// Production never sets this (it defaults to
  /// [ApiSearchIndexRepository]); tests pass a [DemoSearchIndexRepository]
  /// so they never require the FastAPI backend to be running.
  final SearchIndexRepository? searchIndexRepository;

  /// Overrides the real backend-backed legal compliance repository.
  /// Production never sets this (it defaults to
  /// [ApiLegalComplianceRepository]); tests pass a
  /// [DemoLegalComplianceRepository] so they never require the FastAPI
  /// backend to be running.
  final LegalComplianceRepository? legalRepository;

  /// Overrides the real backend-backed analytics repository. Production
  /// never sets this (it defaults to [ApiAnalyticsRepository]); tests pass
  /// a [DemoAnalyticsRepository] so they never require the FastAPI backend
  /// to be running.
  final AnalyticsRepository? analyticsRepository;

  /// Overrides the real backend-backed recommendation governance
  /// repository. Production never sets this (it defaults to
  /// [ApiRecommendationGovernanceRepository]); tests pass a
  /// [DemoRecommendationGovernanceRepository] so they never require the
  /// FastAPI backend to be running.
  final RecommendationGovernanceRepository? recommendationGovernanceRepository;

  /// Overrides the real backend-backed provider analytics repository.
  /// Production never sets this (it defaults to
  /// [ApiProviderAnalyticsRepository]); tests pass a
  /// [DemoProviderAnalyticsRepository] so they never require the FastAPI
  /// backend to be running.
  final ProviderAnalyticsRepository? providerAnalyticsRepository;

  /// Overrides the real backend-backed security repository (sessions,
  /// login history, alerts). Production never sets this (it defaults to
  /// [ApiSecurityRepository]); tests pass a [DemoSecurityRepository] so
  /// they never require the FastAPI backend to be running.
  final SecurityRepository? securityRepository;

  /// Overrides the real backend-backed audit repository. Production never
  /// sets this (it defaults to [ApiAuditRepository]); tests pass a
  /// [DemoAuditRepository] so they never require the FastAPI backend to be
  /// running.
  final AuditRepository? auditRepository;

  /// Overrides the real backend-backed system configuration repository.
  /// Production never sets this (it defaults to
  /// [ApiSystemConfigurationRepository]); tests pass a
  /// [DemoSystemConfigurationRepository] so they never require the FastAPI
  /// backend to be running.
  final SystemConfigurationRepository? systemConfigurationRepository;

  /// Overrides the real backend-backed backup repository. Production
  /// never sets this (it defaults to [ApiBackupRepository]); tests pass a
  /// [DemoBackupRepository] so they never require the FastAPI backend to
  /// be running.
  final BackupRepository? backupRepository;

  /// Overrides the real backend-backed release repository. Production
  /// never sets this (it defaults to [ApiReleaseRepository]); tests pass a
  /// [DemoReleaseRepository] so they never require the FastAPI backend to
  /// be running.
  final ReleaseRepository? releaseRepository;

  /// Overrides the real backend-backed data lifecycle repository.
  /// Production never sets this (it defaults to
  /// [ApiDataLifecycleRepository]); tests pass a
  /// [DemoDataLifecycleRepository] so they never require the FastAPI
  /// backend to be running.
  final DataLifecycleRepository? dataLifecycleRepository;

  /// Overrides the real backend-backed observability repository.
  /// Production never sets this (it defaults to
  /// [ApiObservabilityRepository]); tests pass a
  /// [DemoObservabilityRepository] so they never require the FastAPI
  /// backend to be running.
  final ObservabilityRepository? observabilityRepository;

  /// Overrides the real backend-backed fraud investigation repository.
  /// Production never sets this (it defaults to
  /// [ApiFraudInvestigationRepository]); tests pass a
  /// [DemoFraudInvestigationRepository] so they never require the FastAPI
  /// backend to be running.
  final FraudInvestigationRepository? fraudInvestigationRepository;

  /// Overrides the real backend-backed opportunity collection repository.
  /// Production never sets this (it defaults to
  /// [ApiOpportunityCollectionRepository]); tests pass a
  /// [DemoOpportunityCollectionRepository] so they never require the
  /// FastAPI backend to be running.
  final OpportunityCollectionRepository? collectionRepository;

  /// Overrides the real backend-backed verification repository used by the
  /// Verification Officer dashboard and live queue. Production never sets
  /// this (it defaults to [ApiVerificationRepository]); tests pass one
  /// constructed with a fake `http.Client` so they never require the
  /// FastAPI backend to be running.
  final ApiVerificationRepository? verificationRepository;

  /// Overrides the real backend-backed Premium billing/entitlement
  /// repository used by the Premium landing/pricing screen. Production
  /// never sets this (it defaults to [ApiPremiumRepository]); tests pass a
  /// [DemoPremiumRepository] so they never require the FastAPI backend to
  /// be running.
  final PremiumRepository? premiumRepository;

  /// repository backing every Success Stories / testimonial screen.
  /// Production never sets this (it defaults to
  /// [ApiTestimonialRepository]); tests pass a [DemoTestimonialRepository]
  /// so they never require the FastAPI backend to be running.
  final TestimonialRepository? testimonialRepository;

  @override
  State<ScholarSphereApp> createState() => _ScholarSphereAppState();
}

class _ScholarSphereAppState extends State<ScholarSphereApp> {
  final _navigatorKey = GlobalKey<NavigatorState>();
  late final _securityRepository =
      widget.securityRepository ?? ApiSecurityRepository();
  late final _experienceRepository =
      widget.experienceRepository ?? ApiExperienceRepository();
  final _jobQueueRepository = DemoJobQueueRepository();
  late final _searchIndexRepository =
      widget.searchIndexRepository ?? ApiSearchIndexRepository();
  late final _supportRepository =
      widget.supportRepository ?? ApiSupportRepository();
  late final _calendarRepository =
      widget.calendarRepository ?? ApiCalendarRepository();
  late final _guidanceRepository =
      widget.guidanceRepository ?? ApiApplicationGuidanceRepository();
  late final _lifecycleRepository =
      widget.dataLifecycleRepository ?? ApiDataLifecycleRepository();
  late final _legalRepository =
      widget.legalRepository ?? ApiLegalComplianceRepository();
  late final _fraudInvestigationRepository =
      widget.fraudInvestigationRepository ?? ApiFraudInvestigationRepository();
  late final _taxonomyRepository =
      widget.taxonomyRepository ?? ApiTaxonomyRepository();
  late final _auditRepository = widget.auditRepository ?? ApiAuditRepository();
  late final _configurationRepository =
      widget.systemConfigurationRepository ??
      ApiSystemConfigurationRepository();
  late final _observabilityRepository =
      widget.observabilityRepository ?? ApiObservabilityRepository();
  late final _backupRepository =
      widget.backupRepository ?? ApiBackupRepository();
  late final _releaseRepository =
      widget.releaseRepository ?? ApiReleaseRepository();
  late final _authRepository =
      widget.authRepository ?? FirebaseAuthRepository();
  late final _apiOpportunityRepository =
      widget.apiOpportunityRepository ?? ApiOpportunityRepository();
  late final _profileRepository =
      widget.applicantProfileRepository ?? ApiApplicantProfileRepository();
  late final _notificationRepository =
      widget.notificationRepository ?? ApiNotificationRepository();
  late final _applicationRepository =
      widget.applicationRepository ?? ApiApplicationRepository();
  late final _privacyRepository =
      widget.privacyRepository ?? ApiPrivacyRepository();
  late final _documentRepository =
      widget.documentRepository ?? ApiDocumentRepository();
  late final _premiumRepository =
      widget.premiumRepository ?? ApiPremiumRepository();
  late final _testimonialRepository =
      widget.testimonialRepository ?? ApiTestimonialRepository();
  late final _analyticsRepository =
      widget.analyticsRepository ?? ApiAnalyticsRepository();
  late final _recommendationGovernanceRepository =
      widget.recommendationGovernanceRepository ??
      ApiRecommendationGovernanceRepository();
  final _providerRepository = ApiProviderRepository();
  final _apiProviderOpportunityRepository = ApiProviderOpportunityRepository();
  late final _providerAnalyticsRepository =
      widget.providerAnalyticsRepository ?? ApiProviderAnalyticsRepository();
  late final _sourceRegistryRepository =
      widget.sourceRegistryRepository ?? ApiSourceRegistryRepository();
  late final _moderationRepository =
      widget.moderationRepository ?? ApiModerationRepository();
  late final _apiVerificationRepository =
      widget.verificationRepository ?? ApiVerificationRepository();
  late final _collectionRepository =
      widget.collectionRepository ?? ApiOpportunityCollectionRepository();
  late final _administrationAnalytics = AdministrationAnalyticsService(
    authRepository: _authRepository,
    opportunityRepository: _apiOpportunityRepository,
    applicationRepository: _applicationRepository,
    profileRepository: _profileRepository,
    notificationRepository: _notificationRepository,
    analyticsRepository: _analyticsRepository,
  );
  UserAccount? _user;
  bool _initializingAuthentication = true;
  ExperiencePreferences _experiencePreferences = const ExperiencePreferences();

  @override
  void initState() {
    super.initState();
    _registerBackgroundJobs();
    _restoreAuthentication();
  }

  Future<void> _restoreAuthentication() async {
    final account = await _authRepository.restoreSession();
    if (account != null) {
      await _completeAuthentication(account);
    }
    if (mounted) setState(() => _initializingAuthentication = false);
  }

  void _registerBackgroundJobs() {
    // Feeds the real, shared search index (ApiSearchIndexRepository) from
    // the real opportunity backend. This used to read from
    // DemoOpportunityRepository, which meant every rebuild deleted the
    // entire live search index (POST /search-index/rebuild always prunes
    // first) and then re-populated it with demo IDs the server's own
    // re-validation (_is_real_public_opportunity) rejects, since they never
    // match a real external_opportunities row -- the net effect was a
    // rebuild silently leaving the real index empty. Fixed by reading from
    // _apiOpportunityRepository, the same source every other real screen
    // uses.
    _jobQueueRepository.registerHandler(
      BackgroundJobType.searchIndexUpdate,
      (_) async => _searchIndexRepository.rebuild(
        await _apiOpportunityRepository.getAllForAdministration(),
      ),
    );
    // Deliberately not registering a client-side
    // BackgroundJobType.expiredOpportunityDetection handler against the
    // real backend: scholarsphere_backend already runs this server-side,
    // authoritatively, once a day (Celery beat ->
    // app.tasks.opportunity_sync.detect_expired_opportunities, 01:05 UTC),
    // and ApiOpportunityRepository has no replace()/mutate capability by
    // design -- verification-status transitions are meant to be
    // server-enforced, not set from the client (see Architecture.md,
    // "Architecture Decisions" #7). Re-implementing the same check here
    // against real data would either require inventing a new backend
    // endpoint that duplicates the Celery task, or silently doing nothing
    // useful. See docs/OPPORTUNITY_VERIFICATION_SYSTEM.md SS3.
    _jobQueueRepository.registerHandler(BackgroundJobType.dataCleanup, (
      _,
    ) async {
      const service = UserAccount(
        id: 'system-retention-worker',
        fullName: 'Retention Worker',
        email: 'retention-worker@system.invalid',
        role: UserRole.superAdministrator,
        status: AccountStatus.active,
        emailVerified: true,
      );
      for (final rule in const [
        RetentionRule(
          entityType: RetainedEntityType.opportunity,
          activeDuration: Duration(days: 365),
          archiveDuration: Duration(days: 730),
          deleteFromBackupsAfter: Duration(days: 35),
          archiveExpiredRecords: true,
          retainRejectedForFraudPrevention: false,
        ),
        RetentionRule(
          entityType: RetainedEntityType.document,
          activeDuration: Duration(days: 730),
          archiveDuration: Duration(days: 30),
          deleteFromBackupsAfter: Duration(days: 35),
          archiveExpiredRecords: false,
          retainRejectedForFraudPrevention: false,
        ),
        RetentionRule(
          entityType: RetainedEntityType.auditLog,
          activeDuration: Duration(days: 2555),
          archiveDuration: Duration(days: 365),
          deleteFromBackupsAfter: Duration(days: 35),
          archiveExpiredRecords: true,
          retainRejectedForFraudPrevention: true,
        ),
      ]) {
        await _lifecycleRepository.saveRule(service, rule);
      }
      await _lifecycleRepository.runCleanup(service);
    });
    _jobQueueRepository.enqueue(
      type: BackgroundJobType.searchIndexUpdate,
      payload: const {},
      priority: JobPriority.high,
      deduplicationKey: 'startup-search-index',
    );
    _jobQueueRepository.enqueue(
      type: BackgroundJobType.dataCleanup,
      payload: const {},
      priority: JobPriority.low,
      deduplicationKey: 'scheduled-data-cleanup',
    );
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: _navigatorKey,
      title: 'ScholarSphere',
      debugShowCheckedModeBanner: false,
      theme: buildScholarSphereTheme(
        highContrast: _experiencePreferences.highContrast,
      ),
      builder: (context, child) {
        final media = MediaQuery.of(context);
        return Directionality(
          textDirection: _experiencePreferences.language.isRightToLeft
              ? TextDirection.rtl
              : TextDirection.ltr,
          child: MediaQuery(
            data: media.copyWith(
              textScaler: TextScaler.linear(_experiencePreferences.textScale),
            ),
            child: child ?? const SizedBox.shrink(),
          ),
        );
      },
      home: _buildHome(),
    );
  }

  Widget _buildHome() {
    if (_initializingAuthentication) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final user = _user;
    if (user == null) {
      return AuthScreen(
        repository: _authRepository,
        onAuthenticated: _handleAuthenticated,
      );
    }
    if (user.role == UserRole.applicant) {
      final discovery = DiscoverScreen(
        repository: _apiOpportunityRepository,
        profileRepository: _profileRepository,
        notificationRepository: _notificationRepository,
        applicationRepository: _applicationRepository,
        documentRepository: _documentRepository,
        analyticsRepository: _analyticsRepository,
        securityRepository: _securityRepository,
        privacyRepository: _privacyRepository,
        recommendationGovernanceRepository: _recommendationGovernanceRepository,
        moderationRepository: _moderationRepository,
        experienceRepository: _experienceRepository,
        onExperienceChanged: (preferences) =>
            setState(() => _experiencePreferences = preferences),
        searchIndexRepository: _searchIndexRepository,
        supportRepository: _supportRepository,
        calendarRepository: _calendarRepository,
        guidanceRepository: _guidanceRepository,
        user: user,
        onSignOut: _signOut,
      );
      return ApplicantDashboardScreen(
        user: user,
        opportunityRepository: _apiOpportunityRepository,
        profileRepository: _profileRepository,
        applicationRepository: _applicationRepository,
        notificationRepository: _notificationRepository,
        testimonialRepository: _testimonialRepository,
        opportunityScreen: discovery,
        openApplications: () => _openApplicantApplications(user),
        openSaved: () => _openApplicantApplications(user, savedOnly: true),
        openNotifications: () => _openApplicantNotifications(user),
        openProfile: () => _openApplicantProfile(user),
        openCalendar: () => _openApplicantCalendar(user),
        openDocuments: () => _openApplicantProfile(user),
        openSettings: () => _openApplicantSettings(user),
        openPremium: _openPremium,
        openSuccessStories: _openSuccessStories,
        openShareStory: _openShareStory,
        onSignOut: _signOut,
      );
    }
    if (user.role == UserRole.opportunityProvider) {
      return ProviderAccountScreen(
        user: user,
        providerRepository: _providerRepository,
        opportunityRepository: _apiProviderOpportunityRepository,
        analyticsRepository: _providerAnalyticsRepository,
        onOpenNotifications: () => _openStaffNotifications(user),
        onSignOut: _signOut,
      );
    }
    if (user.role == UserRole.verificationOfficer) {
      return VerificationOfficerDashboardScreen(
        user: user,
        liveRepository: _apiVerificationRepository,
        providerRepository: _providerRepository,
        onOpenNotifications: () => _openStaffNotifications(user),
        onSignOut: _signOut,
      );
    }
    if (user.role == UserRole.moderator) {
      return ModeratorDashboardScreen(
        user: user,
        repository: _moderationRepository,
        testimonialRepository: _testimonialRepository,
        onOpenNotifications: () => _openStaffNotifications(user),
        onSignOut: _signOut,
      );
    }
    if (user.role == UserRole.supportOfficer) {
      return SupportAgentScreen(
        user: user,
        repository: _supportRepository,
        onOpenNotifications: () => _openStaffNotifications(user),
        onSignOut: _signOut,
      );
    }
    if (user.role == UserRole.securityAdministrator) {
      return SecurityAdministratorDashboardScreen(
        user: user,
        securityRepository: _securityRepository,
        auditRepository: _auditRepository,
        onOpenSecurityCenter: () => _openApplicantSettings(user),
        onOpenNotifications: () => _openStaffNotifications(user),
        onSignOut: _signOut,
      );
    }
    if (AccessControlPolicy.allows(user.role, Permission.viewAdministration)) {
      return AdministrationDashboardScreen(
        user: user,
        analytics: _administrationAnalytics,
        authRepository: _authRepository,
        collectionRepository: _collectionRepository,
        sourceRegistryRepository: _sourceRegistryRepository,
        providerRepository: _providerRepository,
        auditRepository: _auditRepository,
        jobQueueRepository: _jobQueueRepository,
        configurationRepository: _configurationRepository,
        observabilityRepository: _observabilityRepository,
        backupRepository: _backupRepository,
        releaseRepository: _releaseRepository,
        lifecycleRepository: _lifecycleRepository,
        legalRepository: _legalRepository,
        fraudInvestigationRepository: _fraudInvestigationRepository,
        taxonomyRepository: _taxonomyRepository,
        onOpenNotifications: () => _openStaffNotifications(user),
        onSignOut: _signOut,
      );
    }
    return RoleWorkspaceScreen(user: user, onSignOut: _signOut);
  }

  void _openApplicantApplications(UserAccount user, {bool savedOnly = false}) {
    _navigatorKey.currentState?.push<void>(
      MaterialPageRoute(
        builder: (_) => ApplicationTrackerScreen(
          userId: user.id,
          repository: _applicationRepository,
          savedOnly: savedOnly,
        ),
      ),
    );
  }

  Future<void> _openApplicantNotifications(UserAccount user) async {
    final opportunities = await _apiOpportunityRepository.getPublished();
    _navigatorKey.currentState?.push<void>(
      MaterialPageRoute(
        builder: (_) => NotificationCenterScreen(
          userId: user.id,
          opportunities: opportunities,
          repository: _notificationRepository,
        ),
      ),
    );
  }

  /// Staff roles (verification, moderation, support, security,
  /// administration) don't browse the published opportunity catalogue the
  /// way applicants do, so there's no natural opportunity list to pass -
  /// an empty list still lets [NotificationCenterScreen] render any
  /// non-opportunity-linked notification correctly.
  void _openStaffNotifications(UserAccount user) {
    _navigatorKey.currentState?.push<void>(
      MaterialPageRoute(
        builder: (_) => NotificationCenterScreen(
          userId: user.id,
          opportunities: const [],
          repository: _notificationRepository,
        ),
      ),
    );
  }

  void _openApplicantProfile(UserAccount user) {
    _navigatorKey.currentState?.push<void>(
      MaterialPageRoute(
        builder: (_) =>
            ApplicantProfileScreen(user: user, repository: _profileRepository),
      ),
    );
  }

  Future<void> _openApplicantCalendar(UserAccount user) async {
    final opportunities = await _apiOpportunityRepository.getPublished();
    final applications = await _applicationRepository.getForUser(user.id);
    _navigatorKey.currentState?.push<void>(
      MaterialPageRoute(
        builder: (_) => CalendarScreen(
          userId: user.id,
          opportunities: opportunities,
          applications: applications,
          repository: _calendarRepository,
        ),
      ),
    );
  }

  void _openPremium() {
    _navigatorKey.currentState?.push<void>(
      MaterialPageRoute(
        builder: (_) => PremiumLandingScreen(repository: _premiumRepository),
      ),
    );
  }

  void _openSuccessStories() {
    _navigatorKey.currentState?.push<void>(
      MaterialPageRoute(
        builder: (_) => SuccessStoriesScreen(
          repository: _testimonialRepository,
          onShareStory: _openShareStory,
        ),
      ),
    );
  }

  void _openShareStory() {
    _navigatorKey.currentState?.push<bool>(
      MaterialPageRoute(
        builder: (_) =>
            ShareSuccessStoryScreen(repository: _testimonialRepository),
      ),
    );
  }

  void _openApplicantSettings(UserAccount user) {
    _navigatorKey.currentState?.push<void>(
      MaterialPageRoute(
        builder: (_) => SecurityPrivacyCenterScreen(
          user: user,
          securityRepository: _securityRepository,
          privacyRepository: _privacyRepository,
          profileRepository: _profileRepository,
          applicationRepository: _applicationRepository,
          documentRepository: _documentRepository,
        ),
      ),
    );
  }

  Future<void> _signOut() async {
    await _authRepository.signOut();
    if (mounted) setState(() => _user = null);
  }

  void _handleAuthenticated(UserAccount account) {
    _completeAuthentication(account);
  }

  Future<void> _completeAuthentication(UserAccount account) async {
    final experience = await _experienceRepository.getPreferences(account.id);
    final consents = await _privacyRepository.getConsents(account.id);
    final active = {
      for (final consent in consents)
        if (consent.isActive) consent.type,
    };
    for (final type in const {
      ConsentType.privacyPolicy,
      ConsentType.termsAndConditions,
    }) {
      if (!active.contains(type)) {
        await _privacyRepository.grantConsent(
          userId: account.id,
          type: type,
          policyVersion: '2026-07',
        );
      }
    }
    if (mounted) {
      setState(() {
        _user = account;
        _experiencePreferences = experience;
      });
    }
  }
}
