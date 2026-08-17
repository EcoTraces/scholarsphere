import 'package:flutter/material.dart';

import '../features/administration/domain/administration_analytics_service.dart';
import '../features/administration/presentation/administration_dashboard_screen.dart';
import '../features/analytics/data/demo_analytics_repository.dart';
import '../features/audit/data/demo_audit_repository.dart';
import '../features/background_jobs/data/demo_job_queue_repository.dart';
import '../features/background_jobs/domain/background_job.dart';
import '../features/calendar/data/demo_calendar_repository.dart';
import '../features/calendar/presentation/calendar_screen.dart';
import '../features/authentication/data/firebase_auth_repository.dart';
import '../features/authentication/domain/auth_repository.dart';
import '../features/authentication/domain/user_account.dart';
import '../features/authentication/presentation/auth_screen.dart';
import '../features/authentication/presentation/role_workspace_screen.dart';
import '../features/applications/data/demo_application_repository.dart';
import '../features/applications/presentation/application_tracker_screen.dart';
import '../features/collection/data/demo_opportunity_collection_repository.dart';
import '../features/dashboard/presentation/applicant_dashboard_screen.dart';
import '../features/documents/data/demo_document_repository.dart';
import '../features/experience/data/demo_experience_repository.dart';
import '../features/experience/domain/experience_preferences.dart';
import '../features/fraud_investigation/data/demo_fraud_investigation_repository.dart';
import '../features/governance/data/demo_data_lifecycle_repository.dart';
import '../features/governance/data/demo_legal_compliance_repository.dart';
import '../features/governance/domain/data_lifecycle.dart';
import '../features/guidance/data/demo_application_guidance_repository.dart';
import '../features/moderation/data/demo_moderation_repository.dart';
import '../features/moderation/presentation/moderator_dashboard_screen.dart';
import '../features/opportunities/data/api_opportunity_repository.dart';
import '../features/opportunities/data/demo_opportunity_repository.dart';
import '../features/opportunities/domain/opportunity.dart';
import '../features/opportunities/domain/opportunity_repository.dart';
import '../features/operations/data/demo_backup_repository.dart';
import '../features/operations/data/demo_observability_repository.dart';
import '../features/operations/data/demo_release_repository.dart';
import '../features/operations/data/demo_system_configuration_repository.dart';
import '../features/opportunities/presentation/discover_screen.dart';
import '../features/providers/data/demo_provider_repository.dart';
import '../features/providers/presentation/provider_account_screen.dart';
import '../features/provider_analytics/data/demo_provider_analytics_repository.dart';
import '../features/sources/data/demo_source_registry_repository.dart';
import '../features/notifications/data/demo_notification_repository.dart';
import '../features/notifications/presentation/notification_center_screen.dart';
import '../features/profiles/data/demo_applicant_profile_repository.dart';
import '../features/profiles/presentation/applicant_profile_screen.dart';
import '../features/privacy/data/demo_privacy_repository.dart';
import '../features/privacy/domain/privacy_models.dart';
import '../features/recommendations/data/demo_recommendation_governance_repository.dart';
import '../features/security/data/demo_security_repository.dart';
import '../features/security/presentation/security_privacy_center_screen.dart';
import '../features/security/presentation/security_administrator_dashboard_screen.dart';
import '../features/search_index/data/demo_search_index_repository.dart';
import '../features/support/data/demo_support_repository.dart';
import '../features/support/presentation/support_agent_screen.dart';
import '../features/taxonomy/data/demo_taxonomy_repository.dart';
import '../features/security/domain/access_control.dart';
import '../features/verification/data/api_verification_repository.dart';
import '../features/verification/data/demo_verification_repository.dart';
import '../features/verification/presentation/verification_officer_dashboard_screen.dart';
import 'theme.dart';

class ScholarSphereApp extends StatefulWidget {
  const ScholarSphereApp({
    super.key,
    this.authRepository,
    this.apiOpportunityRepository,
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

  @override
  State<ScholarSphereApp> createState() => _ScholarSphereAppState();
}

class _ScholarSphereAppState extends State<ScholarSphereApp> {
  final _navigatorKey = GlobalKey<NavigatorState>();
  final _securityRepository = DemoSecurityRepository();
  final _experienceRepository = DemoExperienceRepository();
  final _jobQueueRepository = DemoJobQueueRepository();
  final _searchIndexRepository = DemoSearchIndexRepository();
  final _supportRepository = DemoSupportRepository();
  final _calendarRepository = DemoCalendarRepository();
  final _guidanceRepository = DemoApplicationGuidanceRepository();
  late final _lifecycleRepository = DemoDataLifecycleRepository(
    auditRepository: _auditRepository,
  );
  final _legalRepository = DemoLegalComplianceRepository();
  late final _fraudInvestigationRepository = DemoFraudInvestigationRepository(
    _opportunityRepository,
    _providerRepository,
  );
  final _taxonomyRepository = DemoTaxonomyRepository();
  final _auditRepository = DemoAuditRepository();
  late final _configurationRepository = DemoSystemConfigurationRepository(
    auditRepository: _auditRepository,
  );
  final _observabilityRepository = DemoObservabilityRepository();
  late final _backupRepository = DemoBackupRepository(
    auditRepository: _auditRepository,
  );
  late final _releaseRepository = DemoReleaseRepository(
    auditRepository: _auditRepository,
  );
  late final _authRepository =
      widget.authRepository ?? FirebaseAuthRepository();
  final _opportunityRepository = DemoOpportunityRepository();
  late final _apiOpportunityRepository =
      widget.apiOpportunityRepository ?? ApiOpportunityRepository();
  final _profileRepository = DemoApplicantProfileRepository();
  final _notificationRepository = DemoNotificationRepository();
  final _applicationRepository = DemoApplicationRepository();
  final _privacyRepository = DemoPrivacyRepository();
  late final _documentRepository = DemoDocumentRepository(
    privacyRepository: _privacyRepository,
  );
  final _analyticsRepository = DemoAnalyticsRepository();
  final _recommendationGovernanceRepository =
      DemoRecommendationGovernanceRepository();
  final _providerRepository = DemoProviderRepository();
  final _providerAnalyticsRepository = DemoProviderAnalyticsRepository();
  final _sourceRegistryRepository = DemoSourceRegistryRepository();
  late final _moderationRepository = DemoModerationRepository(
    _opportunityRepository,
    _providerRepository,
  );
  late final _verificationRepository = DemoVerificationRepository(
    _opportunityRepository,
  );
  final _apiVerificationRepository = ApiVerificationRepository();
  late final _collectionRepository = DemoOpportunityCollectionRepository(
    _opportunityRepository,
    sourceRegistry: _sourceRegistryRepository,
  );
  late final _administrationAnalytics = AdministrationAnalyticsService(
    authRepository: _authRepository,
    opportunityRepository: _opportunityRepository,
    applicationRepository: _applicationRepository,
    profileRepository: _profileRepository,
    notificationRepository: _notificationRepository,
    verificationRepository: _verificationRepository,
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
    _jobQueueRepository.registerHandler(
      BackgroundJobType.searchIndexUpdate,
      (_) async => _searchIndexRepository.rebuild(
        await _opportunityRepository.getAllForAdministration(),
      ),
    );
    _jobQueueRepository.registerHandler(
      BackgroundJobType.notificationScheduling,
      (_) => _notificationRepository.processDueNotifications(),
    );
    _jobQueueRepository.registerHandler(
      BackgroundJobType.expiredOpportunityDetection,
      (_) async {
        final now = DateTime.now();
        for (final opportunity
            in await _opportunityRepository.getAllForAdministration()) {
          if (opportunity.deadline.isBefore(now) &&
              opportunity.verificationStatus != VerificationStatus.archived) {
            await _opportunityRepository.replace(
              opportunity.copyWith(
                verificationStatus: VerificationStatus.expired,
              ),
            );
          }
        }
      },
    );
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
      type: BackgroundJobType.expiredOpportunityDetection,
      payload: const {},
      deduplicationKey: 'startup-expiry-check',
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
        opportunityScreen: discovery,
        openApplications: () => _openApplicantApplications(user),
        openSaved: () => _openApplicantApplications(user, savedOnly: true),
        openNotifications: () => _openApplicantNotifications(user),
        openProfile: () => _openApplicantProfile(user),
        openCalendar: () => _openApplicantCalendar(user),
        openDocuments: () => _openApplicantProfile(user),
        openSettings: () => _openApplicantSettings(user),
        onSignOut: _signOut,
      );
    }
    if (user.role == UserRole.opportunityProvider) {
      return ProviderAccountScreen(
        user: user,
        providerRepository: _providerRepository,
        opportunityRepository: _opportunityRepository,
        analyticsRepository: _providerAnalyticsRepository,
        onSignOut: _signOut,
      );
    }
    if (user.role == UserRole.verificationOfficer) {
      return VerificationOfficerDashboardScreen(
        user: user,
        repository: _verificationRepository,
        liveRepository: _apiVerificationRepository,
        providerRepository: _providerRepository,
        onSignOut: _signOut,
      );
    }
    if (user.role == UserRole.moderator) {
      return ModeratorDashboardScreen(
        user: user,
        repository: _moderationRepository,
        onSignOut: _signOut,
      );
    }
    if (user.role == UserRole.supportOfficer) {
      return SupportAgentScreen(
        user: user,
        repository: _supportRepository,
        onSignOut: _signOut,
      );
    }
    if (user.role == UserRole.securityAdministrator) {
      return SecurityAdministratorDashboardScreen(
        user: user,
        securityRepository: _securityRepository,
        auditRepository: _auditRepository,
        onOpenSecurityCenter: () => _openApplicantSettings(user),
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
