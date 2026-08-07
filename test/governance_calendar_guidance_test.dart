import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/authentication/domain/user_account.dart';
import 'package:scholarsphere/features/calendar/data/demo_calendar_repository.dart';
import 'package:scholarsphere/features/calendar/domain/calendar_event.dart';
import 'package:scholarsphere/features/documents/domain/document_readiness.dart';
import 'package:scholarsphere/features/fraud_investigation/data/demo_fraud_investigation_repository.dart';
import 'package:scholarsphere/features/fraud_investigation/domain/fraud_case.dart';
import 'package:scholarsphere/features/fraud_investigation/domain/risk_scoring_service.dart';
import 'package:scholarsphere/features/governance/data/demo_data_lifecycle_repository.dart';
import 'package:scholarsphere/features/governance/data/demo_legal_compliance_repository.dart';
import 'package:scholarsphere/features/governance/domain/data_lifecycle.dart';
import 'package:scholarsphere/features/governance/domain/legal_compliance.dart';
import 'package:scholarsphere/features/guidance/data/demo_application_guidance_repository.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';
import 'package:scholarsphere/features/providers/data/demo_provider_repository.dart';
import 'package:scholarsphere/features/profiles/domain/applicant_profile.dart';
import 'package:scholarsphere/features/taxonomy/data/demo_taxonomy_repository.dart';
import 'package:scholarsphere/features/taxonomy/domain/taxonomy.dart';

void main() {
  test(
    'retention cleanup respects legal holds and verifies deletion',
    () async {
      var now = DateTime.utc(2026, 1, 1);
      final repository = DemoDataLifecycleRepository(clock: () => now);
      final admin = _admin();
      await repository.saveRule(
        admin,
        const RetentionRule(
          entityType: RetainedEntityType.document,
          activeDuration: Duration(days: 30),
          archiveDuration: Duration(days: 30),
          deleteFromBackupsAfter: Duration(days: 35),
          archiveExpiredRecords: true,
          retainRejectedForFraudPrevention: false,
        ),
      );
      await repository.register(
        LifecycleRecord(
          id: 'lifecycle-document-1',
          entityType: RetainedEntityType.document,
          entityId: 'document-1',
          ownerId: 'user-1',
          status: LifecycleStatus.active,
          containsPersonalData: true,
          createdAt: now,
          updatedAt: now,
        ),
      );
      await repository.placeLegalHold(
        admin,
        RetainedEntityType.document,
        'document-1',
        'Regulatory request',
      );
      now = now.add(const Duration(days: 90));
      final cleanup = await repository.runCleanup(admin);
      expect(cleanup.skippedLegalHolds, 1);
      await expectLater(
        repository.permanentlyDelete(
          admin,
          RetainedEntityType.document,
          'document-1',
        ),
        throwsA(isA<StateError>()),
      );

      await repository.register(
        LifecycleRecord(
          id: 'lifecycle-document-2',
          entityType: RetainedEntityType.document,
          entityId: 'document-2',
          ownerId: 'user-1',
          status: LifecycleStatus.active,
          containsPersonalData: true,
          createdAt: now,
          updatedAt: now,
        ),
      );
      await repository.permanentlyDelete(
        admin,
        RetainedEntityType.document,
        'document-2',
      );
      expect(
        await repository.verifyDeletion(
          admin,
          RetainedEntityType.document,
          'document-2',
        ),
        isTrue,
      );
    },
  );

  test('material legal policies require current-version acceptance', () async {
    final repository = DemoLegalComplianceRepository();
    final policy = LegalPolicy(
      id: 'terms',
      type: LegalPolicyType.termsAndConditions,
      version: '2026-07',
      title: 'Terms and Conditions',
      content: RequiredLegalDisclaimers.noGuarantee,
      effectiveAt: DateTime.utc(2026, 8, 1),
      publishedAt: DateTime.utc(2026, 7, 29),
      requiresAcceptance: true,
      materialChange: true,
      publishedBy: 'legal-admin',
    );
    await repository.publish(policy);
    expect(await repository.pendingPolicyNotifications('user'), hasLength(1));
    await repository.accept(
      PolicyAcceptance(
        userId: 'user',
        policyId: policy.id,
        policyVersion: policy.version,
        acceptedAt: DateTime.utc(2026, 7, 29),
        ipAddress: '192.0.2.1',
      ),
    );
    expect(
      await repository.hasAcceptedCurrent(
        'user',
        LegalPolicyType.termsAndConditions,
      ),
      isTrue,
    );
  });

  test(
    'critical fraud cases hide opportunities and support watchlists',
    () async {
      final opportunities = DemoOpportunityRepository();
      final opportunity = (await opportunities.getPublished()).first;
      final repository = DemoFraudInvestigationRepository(
        opportunities,
        DemoProviderRepository(),
      );
      final created = await repository.createCase(
        FraudCase(
          id: 'fraud-1',
          subjectType: FraudSubjectType.opportunity,
          subjectId: opportunity.id,
          risk: _criticalRisk(),
          status: FraudCaseStatus.opened,
          evidence: const [],
          investigatorNotes: const [],
          createdAt: DateTime.utc(2026, 7, 29),
          history: const [],
        ),
      );
      await repository.addWatchlistEntry(
        WatchlistEntry(
          id: 'watch-1',
          subjectType: FraudSubjectType.domain,
          value: 'malicious.example',
          reason: 'Confirmed impersonation domain',
          blocked: true,
          createdAt: DateTime.utc(2026, 7, 29),
          createdBy: 'security-admin',
        ),
      );

      expect(created.status, FraudCaseStatus.restricted);
      expect(
        (await opportunities.getPublished()).any(
          (item) => item.id == opportunity.id,
        ),
        isFalse,
      );
      expect(
        await repository.isBlocked(
          FraudSubjectType.domain,
          'MALICIOUS.EXAMPLE',
        ),
        isTrue,
      );
    },
  );

  test('fraud scoring combines domain, payment, and impersonation signals', () {
    final result = const RiskScoringService().evaluate(
      const RiskScoringInput(
        providerRisk: 90,
        sourceRisk: 90,
        suspiciousDomain: true,
        riskyLink: true,
        paymentRequest: true,
        impersonation: true,
      ),
    );
    expect(result.level, InvestigationRiskLevel.critical);
    expect(result.reasons, hasLength(4));
  });

  test('taxonomy aliases resolve to one canonical academic field', () async {
    final repository = DemoTaxonomyRepository();
    final computing = await repository.resolve(
      TaxonomyType.academicField,
      'Computing',
    );
    final abbreviation = await repository.resolve(
      TaxonomyType.academicField,
      'CS',
    );
    final degree = await repository.resolve(
      TaxonomyType.academicField,
      'BSc Computer Science',
    );
    expect(computing?.id, 'field-computer-science');
    expect(abbreviation?.id, computing?.id);
    expect(degree?.id, computing?.id);
  });

  test('calendar detects conflicts and exports recurring ICS events', () async {
    final repository = DemoCalendarRepository(
      clock: () => DateTime.utc(2026, 7, 29),
    );
    await repository.save(_event('event-1', 10, 12));
    await repository.save(_event('event-2', 11, 13));
    expect(
      (await repository.conflicts('user')).single.overlap,
      const Duration(hours: 1),
    );
    final ics = await repository.exportIcs('user');
    expect(ics, contains('BEGIN:VCALENDAR'));
    expect(ics, contains('RRULE:FREQ=WEEKLY;INTERVAL=1;COUNT=2'));
  });

  test('guidance calculates readiness and preserves the limitation', () async {
    final opportunities = DemoOpportunityRepository();
    final opportunity = (await opportunities.getPublished()).first;
    final repository = DemoApplicationGuidanceRepository(
      clock: () => DateTime.utc(2026, 7, 29),
    );
    final account = _applicant();
    final plan = await repository.createPlan(
      userId: account.id,
      opportunity: opportunity,
      profile: ApplicantProfile.empty(account),
      documents: [
        UserDocument(
          id: 'passport',
          ownerUserId: account.id,
          type: DocumentType.passport,
          fileName: 'passport.pdf',
          uploadedAt: DateTime.utc(2026, 7, 29),
          encryptedAtRest: true,
        ),
      ],
    );
    expect(plan.applicationReadinessScore, lessThan(100));
    expect(plan.missingInformation, isNotEmpty);
    expect(plan.disclaimer, contains('does not'));
  });
}

UserAccount _admin() => const UserAccount(
  id: 'admin',
  fullName: 'Administrator',
  email: 'admin@example.test',
  role: UserRole.administrator,
  status: AccountStatus.active,
  emailVerified: true,
);

UserAccount _applicant() => const UserAccount(
  id: 'applicant',
  fullName: 'Applicant',
  email: 'applicant@example.test',
  role: UserRole.applicant,
  status: AccountStatus.active,
  emailVerified: true,
);

RiskScore _criticalRisk() => const RiskScore(
  overall: 95,
  level: InvestigationRiskLevel.critical,
  providerRisk: 80,
  sourceRisk: 90,
  userBehaviourRisk: 20,
  domainRisk: 100,
  linkRisk: 100,
  paymentRisk: 90,
  impersonationRisk: 100,
  reasons: ['Known malicious domain', 'Institution impersonation'],
);

CalendarEvent _event(String id, int startHour, int endHour) => CalendarEvent(
  id: id,
  userId: 'user',
  title: 'Deadline preparation',
  description: 'Prepare submission',
  type: CalendarEventType.documentSubmission,
  startsAt: DateTime.utc(2026, 8, 1, startHour),
  endsAt: DateTime.utc(2026, 8, 1, endHour),
  timezone: 'UTC',
  reminderMinutes: const {60},
  deadlineState: DeadlineState.upcoming,
  relatedEntityId: null,
  recurrence: const RecurrenceRule(frequency: 'weekly', interval: 1, count: 2),
  createdAt: DateTime.utc(2026, 7, 29),
);
