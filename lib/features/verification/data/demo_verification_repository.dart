import '../../opportunities/data/demo_opportunity_repository.dart';
import '../../opportunities/domain/opportunity.dart';
import '../domain/verification_repository.dart';
import '../domain/verification_review.dart';

class DemoVerificationRepository implements VerificationRepository {
  DemoVerificationRepository(this._opportunities, {DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  final DemoOpportunityRepository _opportunities;
  final DateTime Function() _clock;
  final List<VerificationReview> _reviews = [];

  @override
  Future<List<Opportunity>> getQueue() async {
    final now = _clock();
    for (final review in [..._reviews]) {
      final expiry = review.expiresAt ?? review.nextReviewAt;
      if (review.workflowStatus == VerificationWorkflowStatus.verified &&
          expiry != null &&
          !expiry.isAfter(now)) {
        final opportunity = await _opportunities.getById(review.opportunityId);
        if (opportunity != null && opportunity.isVerified) {
          await _opportunities.replace(
            opportunity.copyWith(
              verificationStatus: VerificationStatus.verificationExpired,
            ),
          );
          _reviews.add(
            review.copyWith(
              workflowStatus: VerificationWorkflowStatus.verificationExpired,
              reviewedAt: now,
            ),
          );
        }
      }
    }
    return _opportunities.getVerificationCandidates();
  }

  @override
  Future<VerificationReview?> getLatestReview(String opportunityId) async =>
      _latest(opportunityId);

  @override
  Future<void> submitReview(VerificationReview review) async {
    if (review.status == VerificationStatus.verified) {
      if (!review.hasOfficialAuthority) {
        throw const VerificationFailure(
          'Verification requires an official institution, sponsor, embassy, '
          'government, or international organization source.',
        );
      }
      if (!review.checklist.legacyPassed) {
        throw const VerificationFailure(
          'Every verification check must pass before approval.',
        );
      }
      if (review.nextReviewAt == null) {
        throw const VerificationFailure(
          'Verified opportunities require a scheduled recheck.',
        );
      }
    }
    final opportunity = await _opportunities.getById(review.opportunityId);
    if (opportunity == null) {
      throw const VerificationFailure('Opportunity no longer exists.');
    }
    _reviews.add(review);
    await _opportunities.replace(
      opportunity.copyWith(
        verificationStatus: review.status,
        lastVerifiedAt: review.status == VerificationStatus.verified
            ? review.reviewedAt
            : opportunity.lastVerifiedAt,
      ),
    );
  }

  @override
  Future<List<VerificationReview>> getAllForAdministration() async =>
      List.unmodifiable(_reviews);

  @override
  Future<VerificationReview> assign({
    required String opportunityId,
    required String officerId,
    required String assignedByUserId,
  }) async {
    final opportunity = await _opportunities.getById(opportunityId);
    if (opportunity == null) {
      throw const VerificationFailure('Opportunity no longer exists.');
    }
    final current = _latest(opportunityId);
    final record = VerificationReview(
      verificationId: _id(),
      opportunityId: opportunityId,
      assignedToUserId: officerId,
      reviewedByUserId: assignedByUserId,
      approvedByUserId: null,
      sourceAuthority: SourceAuthority.unverifiedThirdParty,
      checklist: const VerificationChecklist(),
      status: VerificationStatus.pending,
      workflowStatus: VerificationWorkflowStatus.assigned,
      previousStatus:
          current?.workflowStatus ?? VerificationWorkflowStatus.unreviewed,
      notes: 'Assigned to $officerId',
      reviewedAt: _clock(),
      nextReviewAt: null,
    );
    _reviews.add(record);
    return record;
  }

  @override
  Future<VerificationReview> submitForSecondApproval(
    VerificationReview review,
  ) async {
    if (!review.hasOfficialAuthority) {
      throw const VerificationFailure(
        'An authoritative official source is required.',
      );
    }
    if (!review.checklist.allPassed) {
      throw const VerificationFailure(
        'Every detailed verification check and evidence requirement must pass.',
      );
    }
    if ((review.evidenceLocation ?? '').trim().isEmpty) {
      throw const VerificationFailure('Supporting evidence must be attached.');
    }
    final opportunity = await _opportunities.getById(review.opportunityId);
    if (opportunity == null) {
      throw const VerificationFailure('Opportunity no longer exists.');
    }
    final saved = VerificationReview(
      verificationId: review.verificationId ?? _id(),
      opportunityId: review.opportunityId,
      assignedToUserId: review.assignedToUserId ?? review.reviewedByUserId,
      reviewedByUserId: review.reviewedByUserId,
      approvedByUserId: null,
      sourceAuthority: review.sourceAuthority,
      checklist: review.checklist,
      status: VerificationStatus.pending,
      workflowStatus: VerificationWorkflowStatus.awaitingSecondApproval,
      previousStatus:
          _latest(review.opportunityId)?.workflowStatus ??
          VerificationWorkflowStatus.unreviewed,
      officialSourceUrl: review.officialSourceUrl,
      evidenceLocation: review.evidenceLocation,
      notes: review.notes,
      reviewedAt: review.reviewedAt,
      expiresAt: review.expiresAt,
      nextReviewAt: review.nextReviewAt,
      isCorrection: review.isCorrection,
      appealReason: review.appealReason,
    );
    _reviews.add(saved);
    return saved;
  }

  @override
  Future<VerificationReview> approveSecondLevel({
    required String verificationId,
    required String approverId,
  }) async {
    final review = _reviews.lastWhere(
      (item) => item.verificationId == verificationId,
      orElse: () =>
          throw const VerificationFailure('Verification record was not found.'),
    );
    if (review.workflowStatus !=
        VerificationWorkflowStatus.awaitingSecondApproval) {
      throw const VerificationFailure(
        'This record is not awaiting second-level approval.',
      );
    }
    if (review.reviewedByUserId == approverId) {
      throw const VerificationFailure(
        'Second-level approval requires a different reviewer.',
      );
    }
    final now = _clock();
    final approved = review.copyWith(
      status: VerificationStatus.verified,
      approvedByUserId: approverId,
      workflowStatus: VerificationWorkflowStatus.verified,
      reviewedAt: now,
      expiresAt: review.expiresAt ?? now.add(const Duration(days: 90)),
      nextReviewAt: review.nextReviewAt ?? now.add(const Duration(days: 90)),
    );
    _reviews.add(approved);
    final opportunity = await _opportunities.getById(review.opportunityId);
    if (opportunity == null) {
      throw const VerificationFailure('Opportunity no longer exists.');
    }
    await _opportunities.replace(
      opportunity.copyWith(
        verificationStatus: VerificationStatus.verified,
        lastVerifiedAt: now,
      ),
    );
    return approved;
  }

  @override
  Future<List<VerificationReview>> getHistory(String opportunityId) async =>
      _reviews.where((item) => item.opportunityId == opportunityId).toList();

  @override
  Future<VerificationReview> requestCorrection({
    required String opportunityId,
    required String requestedBy,
    required String notes,
  }) => _createFollowUp(
    opportunityId: opportunityId,
    requestedBy: requestedBy,
    notes: notes,
    status: VerificationWorkflowStatus.reverificationRequired,
    correction: true,
  );

  @override
  Future<VerificationReview> appeal({
    required String opportunityId,
    required String requestedBy,
    required String reason,
  }) => _createFollowUp(
    opportunityId: opportunityId,
    requestedBy: requestedBy,
    notes: 'Appeal: $reason',
    status: VerificationWorkflowStatus.underReview,
    appealReason: reason,
  );

  @override
  Future<VerificationReview> resolveConflict({
    required String opportunityId,
    required String resolverId,
    required VerificationWorkflowStatus resolution,
    required String notes,
  }) async {
    if (resolution != VerificationWorkflowStatus.conditionallyVerified &&
        resolution != VerificationWorkflowStatus.rejected &&
        resolution != VerificationWorkflowStatus.additionalEvidenceRequired) {
      throw const VerificationFailure(
        'Conflict resolution must be conditional approval, rejection, or an evidence request.',
      );
    }
    final previous = _latest(opportunityId);
    if (previous == null) {
      throw const VerificationFailure('No verification history exists.');
    }
    final record = VerificationReview(
      verificationId: _id(),
      opportunityId: opportunityId,
      assignedToUserId: previous.assignedToUserId,
      reviewedByUserId: previous.reviewedByUserId,
      approvedByUserId: resolverId,
      sourceAuthority: previous.sourceAuthority,
      checklist: previous.checklist,
      status: resolution == VerificationWorkflowStatus.rejected
          ? VerificationStatus.rejected
          : VerificationStatus.incomplete,
      workflowStatus: resolution,
      previousStatus: previous.workflowStatus,
      officialSourceUrl: previous.officialSourceUrl,
      evidenceLocation: previous.evidenceLocation,
      notes: 'Conflict resolution: $notes',
      reviewedAt: _clock(),
      nextReviewAt: previous.nextReviewAt,
    );
    _reviews.add(record);
    final opportunity = await _opportunities.getById(opportunityId);
    if (opportunity != null) {
      await _opportunities.replace(
        opportunity.copyWith(verificationStatus: record.status),
      );
    }
    return record;
  }

  Future<VerificationReview> _createFollowUp({
    required String opportunityId,
    required String requestedBy,
    required String notes,
    required VerificationWorkflowStatus status,
    bool correction = false,
    String? appealReason,
  }) async {
    final previous = _latest(opportunityId);
    if (previous == null) {
      throw const VerificationFailure('No verification history exists.');
    }
    final record = VerificationReview(
      verificationId: _id(),
      opportunityId: opportunityId,
      assignedToUserId: previous.assignedToUserId,
      reviewedByUserId: requestedBy,
      sourceAuthority: previous.sourceAuthority,
      checklist: previous.checklist,
      status: VerificationStatus.pending,
      workflowStatus: status,
      previousStatus: previous.workflowStatus,
      officialSourceUrl: previous.officialSourceUrl,
      evidenceLocation: previous.evidenceLocation,
      notes: notes,
      reviewedAt: _clock(),
      nextReviewAt: previous.nextReviewAt,
      isCorrection: correction,
      appealReason: appealReason,
    );
    _reviews.add(record);
    return record;
  }

  VerificationReview? _latest(String opportunityId) {
    final matches = _reviews.where(
      (item) => item.opportunityId == opportunityId,
    );
    return matches.isEmpty ? null : matches.last;
  }

  String _id() =>
      'verification-${_clock().microsecondsSinceEpoch}-${_reviews.length}';
}
