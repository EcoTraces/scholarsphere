import '../../opportunities/data/demo_opportunity_repository.dart';
import '../../opportunities/domain/opportunity.dart';
import '../../providers/domain/provider_repository.dart';
import '../domain/fraud_case.dart';
import '../domain/fraud_investigation_repository.dart';

class DemoFraudInvestigationRepository implements FraudInvestigationRepository {
  DemoFraudInvestigationRepository(
    this._opportunities,
    this._providers, {
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now;

  final DemoOpportunityRepository _opportunities;
  final ProviderRepository _providers;
  final DateTime Function() _clock;
  final Map<String, FraudCase> _cases = {};
  final List<WatchlistEntry> _watchlist = [];

  @override
  Future<FraudCase> createCase(FraudCase fraudCase) async {
    if (_cases.values.any(
      (item) =>
          item.subjectType == fraudCase.subjectType &&
          item.subjectId == fraudCase.subjectId &&
          !_closed(item.status),
    )) {
      throw const FraudInvestigationFailure(
        'An open fraud case already exists for this subject.',
      );
    }
    final recorded = fraudCase.copyWith(
      history: [
        ...fraudCase.history,
        'Risk assessed at ${_clock().toUtc().toIso8601String()}.',
      ],
    );
    _cases[fraudCase.id] = recorded;
    if (fraudCase.risk.level == InvestigationRiskLevel.critical) {
      await _automatedRestriction(recorded);
      final restricted = recorded.copyWith(
        status: FraudCaseStatus.restricted,
        history: [
          ...recorded.history,
          'Critical automated control applied; security review required.',
        ],
      );
      _cases[fraudCase.id] = restricted;
      return restricted;
    }
    return recorded;
  }

  @override
  Future<FraudCase> assign(String caseId, String investigatorId) async {
    final current = _require(caseId);
    final updated = current.copyWith(
      status: FraudCaseStatus.assigned,
      assignedInvestigatorId: investigatorId,
      history: [...current.history, 'Assigned to $investigatorId.'],
    );
    _cases[caseId] = updated;
    return updated;
  }

  @override
  Future<FraudCase> addEvidence(String caseId, FraudEvidence evidence) async {
    final current = _require(caseId);
    final updated = current.copyWith(
      evidence: [...current.evidence, evidence],
      history: [...current.history, 'Evidence ${evidence.id} collected.'],
    );
    _cases[caseId] = updated;
    return updated;
  }

  @override
  Future<FraudCase> addNote(
    String caseId,
    String investigatorId,
    String note,
  ) async {
    final current = _require(caseId);
    if (current.assignedInvestigatorId != investigatorId) {
      throw const FraudInvestigationFailure(
        'Only the assigned investigator can add notes.',
      );
    }
    final updated = current.copyWith(
      status: FraudCaseStatus.investigating,
      investigatorNotes: [...current.investigatorNotes, note],
    );
    _cases[caseId] = updated;
    return updated;
  }

  @override
  Future<FraudCase> restrict(String caseId, String investigatorId) async {
    final current = _require(caseId);
    if (current.evidence.isEmpty) {
      throw const FraudInvestigationFailure(
        'A restriction requires supporting evidence.',
      );
    }
    await _automatedRestriction(current);
    final updated = current.copyWith(
      status: FraudCaseStatus.restricted,
      history: [...current.history, 'Restricted by $investigatorId.'],
    );
    _cases[caseId] = updated;
    return updated;
  }

  @override
  Future<FraudCase> appeal(
    String caseId,
    String subjectId,
    String reason,
  ) async {
    final current = _require(caseId);
    if (current.subjectId != subjectId ||
        current.status != FraudCaseStatus.restricted) {
      throw const FraudInvestigationFailure(
        'Only a restricted subject can appeal.',
      );
    }
    final updated = current.copyWith(
      status: FraudCaseStatus.appealed,
      appealReason: reason,
      history: [...current.history, 'Appeal submitted.'],
    );
    _cases[caseId] = updated;
    return updated;
  }

  @override
  Future<void> addWatchlistEntry(WatchlistEntry entry) async {
    final normalized = entry.value.trim().toLowerCase();
    if (_watchlist.any(
      (item) =>
          item.subjectType == entry.subjectType &&
          item.value.toLowerCase() == normalized,
    )) {
      throw const FraudInvestigationFailure('Watchlist entry already exists.');
    }
    _watchlist.add(entry);
  }

  @override
  Future<bool> isBlocked(FraudSubjectType type, String value) async =>
      _watchlist.any(
        (item) =>
            item.blocked &&
            item.subjectType == type &&
            item.value.toLowerCase() == value.trim().toLowerCase(),
      );

  @override
  Future<List<FraudCase>> queue() async =>
      _cases.values.where((item) => !_closed(item.status)).toList();

  @override
  Future<FraudAnalytics> analytics() async {
    final byType = <FraudSubjectType, int>{};
    for (final item in _cases.values) {
      byType.update(item.subjectType, (count) => count + 1, ifAbsent: () => 1);
    }
    return FraudAnalytics(
      openCases: _cases.values.where((item) => !_closed(item.status)).length,
      criticalCases: _cases.values
          .where((item) => item.risk.level == InvestigationRiskLevel.critical)
          .length,
      restrictedSubjects: _cases.values
          .where((item) => item.status == FraudCaseStatus.restricted)
          .length,
      watchlistEntries: _watchlist.length,
      bySubjectType: byType,
    );
  }

  Future<void> _automatedRestriction(FraudCase fraudCase) async {
    if (fraudCase.subjectType == FraudSubjectType.opportunity) {
      final opportunity = await _opportunities.getById(fraudCase.subjectId);
      if (opportunity != null) {
        await _opportunities.replace(
          opportunity.copyWith(
            verificationStatus: VerificationStatus.suspicious,
          ),
        );
      }
    } else if (fraudCase.subjectType == FraudSubjectType.provider) {
      await _providers.suspend(
        fraudCase.subjectId,
        'Fraud investigation restriction.',
      );
    }
  }

  FraudCase _require(String id) {
    final value = _cases[id];
    if (value == null) {
      throw const FraudInvestigationFailure('Fraud case was not found.');
    }
    return value;
  }

  bool _closed(FraudCaseStatus status) => {
    FraudCaseStatus.resolved,
    FraudCaseStatus.rejected,
    FraudCaseStatus.closed,
  }.contains(status);
}
