import '../../opportunities/data/demo_opportunity_repository.dart';
import '../../opportunities/domain/opportunity.dart';
import '../../providers/domain/provider_repository.dart';
import '../domain/moderation_case.dart';
import '../domain/moderation_repository.dart';

class DemoModerationRepository implements ModerationRepository {
  DemoModerationRepository(
    this._opportunities,
    this._providers, {
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now;

  final DemoOpportunityRepository _opportunities;
  final ProviderRepository _providers;
  final DateTime Function() _clock;
  final Map<String, ModerationCase> _cases = {};
  final List<ModerationWarning> _warnings = [];

  @override
  Future<ModerationCase> submit(ModerationCase report) async {
    final duplicate = _cases.values.any(
      (item) =>
          item.reporterId == report.reporterId &&
          item.entityType == report.entityType &&
          item.entityId == report.entityId &&
          item.reportType == report.reportType &&
          !_closed(item.status),
    );
    if (duplicate) {
      throw const ModerationFailure(
        'An equivalent open report already exists.',
      );
    }
    _cases[report.id] = report;
    return report;
  }

  @override
  Future<List<ModerationCase>> getQueue() async =>
      _cases.values.where((item) => !_closed(item.status)).toList()
        ..sort((a, b) => a.createdAt.compareTo(b.createdAt));

  @override
  Future<List<ModerationCase>> getForReporter(String reporterId) async =>
      _cases.values.where((item) => item.reporterId == reporterId).toList();

  @override
  Future<ModerationCase> assign(String caseId, String moderatorId) =>
      transition(
        caseId: caseId,
        actorId: moderatorId,
        status: ModerationStatus.underReview,
        notes: 'Assigned to moderator.',
      );

  @override
  Future<ModerationCase> transition({
    required String caseId,
    required String actorId,
    required ModerationStatus status,
    required String notes,
    bool hideContent = false,
  }) async {
    final current = _require(caseId);
    final history = [
      ...current.history,
      ModerationHistoryEntry(
        status: status,
        actorId: actorId,
        notes: notes,
        createdAt: _clock(),
      ),
    ];
    final updated = current.copyWith(
      status: status,
      assignedModeratorId: current.assignedModeratorId ?? actorId,
      moderationNotes: notes,
      temporarilyHidden: hideContent || current.temporarilyHidden,
      history: history,
    );
    _cases[caseId] = updated;
    await _applyAction(updated, status, hideContent);
    return updated;
  }

  @override
  Future<ModerationCase> appeal(
    String caseId,
    String appellantId,
    String reason,
  ) async {
    final current = _require(caseId);
    if (!_closed(current.status)) {
      throw const ModerationFailure('Only decided cases can be appealed.');
    }
    final updated = current.copyWith(
      status: ModerationStatus.escalated,
      appealReason: reason,
      history: [
        ...current.history,
        ModerationHistoryEntry(
          status: ModerationStatus.escalated,
          actorId: appellantId,
          notes: 'Appeal: $reason',
          createdAt: _clock(),
        ),
      ],
    );
    _cases[caseId] = updated;
    return updated;
  }

  @override
  Future<ModerationAnalytics> analytics() async {
    final counts = <String, int>{};
    for (final report in _cases.values) {
      counts.update(report.entityId, (value) => value + 1, ifAbsent: () => 1);
    }
    counts.removeWhere((_, count) => count < 2);
    return ModerationAnalytics(
      totalReports: _cases.length,
      openReports: _cases.values.where((item) => !_closed(item.status)).length,
      removedContent: _cases.values
          .where((item) => item.status == ModerationStatus.contentRemoved)
          .length,
      suspendedProviders: _cases.values
          .where((item) => item.status == ModerationStatus.providerSuspended)
          .length,
      repeatOffenders: counts,
    );
  }

  @override
  Future<ModerationWarning> issueWarning({
    required String caseId,
    required String moderatorId,
    required String reason,
  }) async {
    final report = _require(caseId);
    if (report.entityType == ReportedEntityType.opportunity) {
      throw const ModerationFailure(
        'Warnings can only be issued to providers or users.',
      );
    }
    final warning = ModerationWarning(
      id: 'warning-${_clock().microsecondsSinceEpoch}-${_warnings.length}',
      entityType: report.entityType,
      entityId: report.entityId,
      reason: reason,
      issuedBy: moderatorId,
      issuedAt: _clock(),
      caseId: caseId,
    );
    _warnings.add(warning);
    await transition(
      caseId: caseId,
      actorId: moderatorId,
      status: ModerationStatus.resolved,
      notes: '${report.entityType.name} warning issued: $reason',
    );
    return warning;
  }

  @override
  Future<List<ModerationWarning>> warningsFor(
    ReportedEntityType entityType,
    String entityId,
  ) async => _warnings
      .where(
        (warning) =>
            warning.entityType == entityType && warning.entityId == entityId,
      )
      .toList();

  Future<void> _applyAction(
    ModerationCase report,
    ModerationStatus status,
    bool hide,
  ) async {
    if (report.entityType == ReportedEntityType.opportunity &&
        (hide || status == ModerationStatus.contentRemoved)) {
      final opportunity = await _opportunities.getById(report.entityId);
      if (opportunity != null) {
        await _opportunities.replace(
          opportunity.copyWith(
            verificationStatus: status == ModerationStatus.contentRemoved
                ? VerificationStatus.archived
                : VerificationStatus.suspicious,
          ),
        );
      }
    }
    if (report.entityType == ReportedEntityType.provider &&
        status == ModerationStatus.providerSuspended) {
      await _providers.suspend(report.entityId, report.moderationNotes ?? '');
    }
  }

  ModerationCase _require(String id) {
    final value = _cases[id];
    if (value == null) throw const ModerationFailure('Report was not found.');
    return value;
  }

  bool _closed(ModerationStatus status) => {
    ModerationStatus.resolved,
    ModerationStatus.rejected,
    ModerationStatus.contentCorrected,
    ModerationStatus.contentRemoved,
    ModerationStatus.providerSuspended,
    ModerationStatus.closed,
  }.contains(status);
}
